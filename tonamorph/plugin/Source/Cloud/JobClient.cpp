#include "Cloud/JobClient.h"

#include "Core/Strings.h"

#include <memory>
#include <utility>

namespace tonamorph::cloud
{

namespace
{

/** Contract §2 fallback cadence when the SSE stream is unavailable. */
constexpr int pollIntervalMs = 1000;
/** Stop polling after ten minutes so a job that never resolves cannot poll forever. */
constexpr int maxPollAttempts = 600;

/** Repeats `tick` on the message thread until it returns false. The scheduled lambda owns
    the shared state, so nothing keeps itself alive once the ticking stops. */
void scheduleRepeating (int intervalMs, std::shared_ptr<std::function<bool()>> tick)
{
    juce::Timer::callAfterDelay (intervalMs, [intervalMs, tick]
    {
        if (tick != nullptr && *tick != nullptr && (*tick)())
            scheduleRepeating (intervalMs, tick);
    });
}

/** The strings table is UTF-8 (ellipses, dashes); juce::String (const char*) is ASCII-only. */
juce::String text (const char* utf8)
{
    return juce::String::fromUTF8 (utf8);
}

ApiError makeError (const juce::String& code, const juce::String& message, int httpStatus = 0)
{
    ApiError error;
    error.code = code;
    error.message = message;
    error.httpStatus = httpStatus;
    return error;
}

bool isCancellation (const ApiError& error) noexcept
{
    return error.code == "cancelled";
}

/** GTM Appendix B §3 per-stage progress strings. */
juce::String describeStage (JobStage stage)
{
    switch (stage)
    {
        case JobStage::Upload:     return text (strings::stageUploading);
        case JobStage::Separate:   return text (strings::stageSeparating);
        case JobStage::Transcribe: return text (strings::stageTranscribing);
        case JobStage::Analyze:    return text (strings::stageAnalyzing);
        case JobStage::Package:    return text (strings::stagePackaging);
        case JobStage::Done:       return text (strings::stagePackaging);
    }

    return text (strings::stagePackaging);
}

} // namespace

//==============================================================================
JobClient::JobClient (ApiClient& client, AuthManager& authToUse, juce::File cacheRootToUse)
    : api (client),
      auth (authToUse),
      cacheRoot (std::move (cacheRootToUse)),
      encodePool (juce::ThreadPoolOptions{}.withThreadName (juce::String (text (strings::productName)) + " Encoder")
                                           .withNumberOfThreads (1))
{
}

JobClient::~JobClient()
{
    lifetime->store (false, std::memory_order_release);

    if (activeRequest != ApiClient::invalidRequest)
        api.cancel (activeRequest);

    for (const auto id : downloadRequests)
        api.cancel (id);

    encodePool.removeAllJobs (true, 5000);
}

juce::File JobClient::defaultCacheRoot()
{
    return juce::File::getSpecialLocation (juce::File::userApplicationDataDirectory)
               .getChildFile (text (strings::productName))
               .getChildFile ("jobs");
}

juce::String JobClient::toString (State state)
{
    switch (state)
    {
        case State::Idle:        return "Idle";
        case State::Encoding:    return "Encoding";
        case State::Submitting:  return "Submitting";
        case State::Queued:      return "Queued";
        case State::Running:     return "Running";
        case State::Downloading: return "Downloading";
        case State::Ready:       return "Ready";
        case State::Failed:      return "Failed";
        case State::Cancelled:   return "Cancelled";
    }

    return "Idle";
}

//==============================================================================
void JobClient::submitFile (const juce::File& audioFile, JobOptions options)
{
    if (! audioFile.existsAsFile())
    {
        reset();
        fail (makeError ("not_found", "That file could not be opened: " + audioFile.getFileName()));
        return;
    }

    if (! beginSubmission())
        return;

    startEncoding ([audioFile] { return UploadEncoder::encodeFile (audioFile); }, std::move (options));
}

void JobClient::submitBuffer (const juce::AudioBuffer<float>& audio, double sampleRate, JobOptions options)
{
    if (! beginSubmission())
        return;

    startEncoding ([copy = juce::AudioBuffer<float> (audio), sampleRate]
                   { return UploadEncoder::encodeBuffer (copy, sampleRate); },
                   std::move (options));
}

void JobClient::loadCachedJob (const juce::String& jobIdToLoad)
{
    if (isRunning())
        cancel();

    reset();
    jobId = jobIdToLoad;

    if (jobIdToLoad.isEmpty())
    {
        fail (makeError ("cache_missing", text (strings::errorCacheMissing)));
        return;
    }

    if (loadResultFromCache (getJobDirectory()))
    {
        stage = JobStage::Done;
        progress = 1.0;
        setState (State::Ready);
        return;
    }

    // Without a session the server cannot be asked for the job again, so the cache was all
    // there was.
    if (! api.hasCredentials())
    {
        fail (makeError ("cache_missing", text (strings::errorCacheMissing)));
        return;
    }

    setState (State::Queued);

    activeRequest = api.getJob (jobIdToLoad, [this, guard = lifetime] (ApiClient::Response<JobStatus> response)
    {
        if (! guard->load (std::memory_order_acquire))
            return;

        activeRequest = ApiClient::invalidRequest;

        if (state != State::Queued)
            return;

        if (! response.ok())
        {
            const auto loadError = response.error.value_or (ApiError::transport (text (strings::errorCacheMissing)));

            if (isCancellation (loadError))
                return;

            // A job the server no longer has (404) means the cache is all that was left of
            // it; transport and auth failures keep their own codes so the UI can say so.
            if (loadError.httpStatus == 404)
                fail (makeError ("cache_missing", text (strings::errorCacheMissing), 404));
            else
                fail (loadError);

            return;
        }

        const auto& status = *response.value;

        if (status.status != JobState::Succeeded || ! status.result.has_value() || status.result->isExpired())
        {
            fail (makeError ("cache_missing", text (strings::errorCacheMissing)));
            return;
        }

        downloadAssets (*status.result);
    });
}

void JobClient::cancel()
{
    if (! isRunning())
        return;

    const bool wasQueued = (state == State::Queued);

    if (activeRequest != ApiClient::invalidRequest)
    {
        api.cancel (activeRequest);
        activeRequest = ApiClient::invalidRequest;
    }

    for (const auto id : downloadRequests)
        api.cancel (id);

    downloadRequests.clear();
    pendingDownloads = 0;

    // Contract §2: a queued job releases its reservation, a running one answers 409.
    if (wasQueued && jobId.isNotEmpty())
        api.cancelJob (jobId, {});

    setState (State::Cancelled);
}

void JobClient::reset()
{
    jobId.clear();
    result.reset();
    error.reset();
    inputTruncated = false;
    pollingFallback = false;
    progress = 0.0;
    stage = JobStage::Upload;
    setState (State::Idle);
}

//==============================================================================
bool JobClient::isRunning() const noexcept
{
    return state == State::Encoding || state == State::Submitting || state == State::Queued
        || state == State::Running || state == State::Downloading;
}

juce::String JobClient::getStatusMessage() const
{
    const auto percent = " " + juce::String (juce::roundToInt (juce::jlimit (0.0, 1.0, progress) * 100.0)) + " %";

    if (pollingFallback && (state == State::Queued || state == State::Running))
        return text (strings::errorLostContact);

    switch (state)
    {
        case State::Idle:        return text (strings::dropZone);
        case State::Encoding:    return text (strings::stageUploading);
        case State::Submitting:  return text (strings::stageUploading) + percent;
        case State::Queued:      return text (strings::stageQueued);
        case State::Running:     return describeStage (stage) + percent;
        case State::Downloading: return text (strings::stagePackaging) + percent;
        case State::Ready:       return text (strings::ready);
        case State::Cancelled:   return text (strings::cancelled);
        case State::Failed:      return error.has_value() ? error->message : juce::String (text (strings::errorGeneric));
    }

    return toString (state);
}

bool JobClient::isStemAvailable (const juce::String& stemName) const
{
    if (! result.has_value() || (state != State::Downloading && state != State::Ready))
        return false;

    const auto* stem = result->findStem (stemName);
    return stem != nullptr && getStemFile (stemName).existsAsFile();
}

//==============================================================================
void JobClient::setCacheRoot (const juce::File& newRoot)
{
    cacheRoot = newRoot;
}

juce::File JobClient::getJobDirectory() const
{
    return jobDirectoryFor (cacheRoot, jobId);
}

juce::File JobClient::jobDirectoryFor (const juce::File& root, const juce::String& id)
{
    return root.getChildFile (id);
}

juce::File JobClient::getStemFile (const juce::String& stemName) const
{
    return getJobDirectory().getChildFile (stemName + ".wav");
}

juce::File JobClient::getMidiFile() const
{
    return getJobDirectory().getChildFile ("score.mid");
}

juce::File JobClient::getResultFile() const
{
    return getJobDirectory().getChildFile ("result.json");
}

void JobClient::clearCache()
{
    if (cacheRoot.isDirectory())
        cacheRoot.deleteRecursively();
}

//==============================================================================
void JobClient::setState (State newState)
{
    state = newState;
    sendChangeMessage();
}

void JobClient::fail (const ApiError& apiError)
{
    error = apiError;
    setState (State::Failed);
}

bool JobClient::beginSubmission()
{
    if (isRunning())
        cancel();

    jobId.clear();
    result.reset();
    error.reset();
    inputTruncated = false;
    pollingFallback = false;
    progress = 0.0;
    stage = JobStage::Upload;

    // Contract §3: a known-empty balance is refused before any upload happens.
    if (auth.getBalance().has_value() && auth.getAvailableCredits() <= 0)
    {
        fail (makeError ("insufficient_credits", "You have no credits left", 402));
        return false;
    }

    return true;
}

void JobClient::startEncoding (std::function<UploadEncoder::Result()> encode, JobOptions options)
{
    setState (State::Encoding);

    encodePool.addJob ([this, guard = lifetime, encode = std::move (encode), options = std::move (options)]
    {
        auto encoded = std::make_shared<UploadEncoder::Result> (encode());

        juce::MessageManager::callAsync ([this, guard, encoded, options]
        {
            if (guard->load (std::memory_order_acquire))
                onEncoded (*encoded, options);
        });
    });
}

void JobClient::onEncoded (const UploadEncoder::Result& encoded, const JobOptions& options)
{
    if (state != State::Encoding)
        return;

    if (! encoded.ok())
    {
        fail (makeError ("encode_failed", encoded.errorMessage.isNotEmpty() ? encoded.errorMessage
                                                                           : juce::String ("Could not read that audio")));
        return;
    }

    inputTruncated = encoded.truncated;

    auto submitOptions = options;
    submitOptions.clientSampleRate = encoded.sampleRate;

    setState (State::Submitting);
    submit (encoded.flacData, submitOptions);
}

void JobClient::submit (const juce::MemoryBlock& flacData, const JobOptions& options)
{
    activeRequest = api.submitJob (flacData, UploadEncoder::fileName, UploadEncoder::mimeType, options,
                                   [this, guard = lifetime] (ApiClient::Response<JobSubmitResponse> response)
                                   {
                                       if (! guard->load (std::memory_order_acquire))
                                           return;

                                       activeRequest = ApiClient::invalidRequest;

                                       if (state != State::Submitting)
                                           return;

                                       if (! response.ok())
                                       {
                                           const auto submitError = response.error.value_or (ApiError::transport ("Could not start the job"));

                                           if (! isCancellation (submitError))
                                               fail (submitError);

                                           return;
                                       }

                                       onSubmitted (*response.value);
                                   },
                                   [this, guard = lifetime] (juce::int64 bytesDone, juce::int64 bytesTotal)
                                   {
                                       if (! guard->load (std::memory_order_acquire) || state != State::Submitting || bytesTotal <= 0)
                                           return;

                                       progress = juce::jlimit (0.0, 1.0, static_cast<double> (bytesDone)
                                                                              / static_cast<double> (bytesTotal));
                                       sendChangeMessage();
                                   });
}

void JobClient::onSubmitted (const JobSubmitResponse& response)
{
    jobId = response.jobId;
    auth.updateBalance (response.balance);

    stage = JobStage::Upload;
    progress = 0.0;
    setState (State::Queued);

    streamEvents();
}

void JobClient::streamEvents()
{
    activeRequest = api.streamJobEvents (jobId,
                                         [this, guard = lifetime] (const JobEvent& event)
                                         {
                                             if (guard->load (std::memory_order_acquire))
                                                 onEvent (event);
                                         },
                                         [this, guard = lifetime] (ApiClient::Response<JobStatus> response)
                                         {
                                             if (guard->load (std::memory_order_acquire))
                                                 onStreamFinished (response);
                                         });
}

void JobClient::onEvent (const JobEvent& event)
{
    if (event.type != JobEvent::Type::Progress)
        return;   // result / error events arrive again as the stream's final status

    if (state != State::Queued && state != State::Running)
        return;

    stage = event.stage;
    progress = event.progress;

    if (state == State::Queued)
        setState (State::Running);
    else
        sendChangeMessage();
}

void JobClient::onStreamFinished (const ApiClient::Response<JobStatus>& finalStatus)
{
    activeRequest = ApiClient::invalidRequest;

    if (state != State::Queued && state != State::Running)
        return;

    // Applies a JobStatus from either the stream or a poll; true once the job is terminal.
    auto applyStatus = [this] (const JobStatus& status)
    {
        stage = status.stage;
        progress = juce::jlimit (0.0, 1.0, status.progress);

        switch (status.status)
        {
            case JobState::Succeeded:
                if (status.result.has_value())
                    downloadAssets (*status.result);
                else
                    fail (makeError ("invalid_response", "The job finished without a result"));

                return true;

            case JobState::Failed:
                fail (status.error.value_or (makeError ("internal_error", "The job failed")));
                return true;

            case JobState::Cancelled:
                setState (State::Cancelled);
                return true;

            case JobState::Running:
                if (state == State::Queued)
                    setState (State::Running);
                else
                    sendChangeMessage();

                return false;

            case JobState::Queued:
                sendChangeMessage();
                return false;
        }

        return false;
    };

    if (finalStatus.ok())
    {
        applyStatus (*finalStatus.value);
        return;
    }

    const auto streamError = finalStatus.error.value_or (ApiError::transport ("The job stream stopped"));

    if (isCancellation (streamError))
        return;

    if (streamError.isUnauthorized() || streamError.httpStatus == 404)
    {
        fail (streamError);
        return;
    }

    // The stream is unavailable: fall back to polling GET /v1/jobs/{id} once a second.
    pollingFallback = true;
    sendChangeMessage();

    auto attempts = std::make_shared<int> (0);
    auto tick = std::make_shared<std::function<bool()>>();

    *tick = [this, guard = lifetime, applyStatus, attempts]
    {
        if (! guard->load (std::memory_order_acquire))
            return false;

        if (state != State::Queued && state != State::Running)
            return false;

        if (activeRequest != ApiClient::invalidRequest)
            return true;   // a poll is still in flight

        if (++(*attempts) > maxPollAttempts)
        {
            fail (makeError ("lost_contact", text (strings::errorLostContact)));
            return false;
        }

        activeRequest = api.getJob (jobId, [this, guard, applyStatus] (ApiClient::Response<JobStatus> response)
        {
            if (! guard->load (std::memory_order_acquire))
                return;

            activeRequest = ApiClient::invalidRequest;

            if (state != State::Queued && state != State::Running)
                return;

            if (response.ok())
            {
                applyStatus (*response.value);
                return;
            }

            const auto pollError = response.error.value_or (ApiError::transport ("Lost contact with the job"));

            if (! isCancellation (pollError) && (pollError.isUnauthorized() || pollError.httpStatus == 404))
                fail (pollError);
        });

        return true;
    };

    scheduleRepeating (pollIntervalMs, tick);
}

void JobClient::downloadAssets (const JobResult& jobResult)
{
    if (jobResult.jobId.isNotEmpty())
        jobId = jobResult.jobId;

    result = jobResult;
    inputTruncated = inputTruncated || jobResult.input.truncated;

    const auto directory = getJobDirectory();
    directory.createDirectory();
    saveResultToCache (jobResult);

    downloadRequests.clear();
    pendingDownloads = 0;
    stage = JobStage::Package;
    progress = 0.0;
    setState (State::Downloading);

    struct Asset
    {
        juce::String name;
        juce::String url;
        juce::File destination;
    };

    std::vector<Asset> assets;

    for (const auto& stem : jobResult.stems)
        if (stem.url.isNotEmpty())
            assets.push_back ({ stem.name, stem.url, getStemFile (stem.name) });

    if (jobResult.midi.url.isNotEmpty())
        assets.push_back ({ "score.mid", jobResult.midi.url, getMidiFile() });

    if (assets.empty())
    {
        stage = JobStage::Done;
        progress = 1.0;
        setState (State::Ready);
        return;
    }

    pendingDownloads = static_cast<int> (assets.size());

    for (const auto& asset : assets)
    {
        const auto id = api.downloadFile (juce::URL (asset.url), asset.destination,
                                          [this, guard = lifetime, name = asset.name] (ApiClient::Response<juce::File> response)
                                          {
                                              if (guard->load (std::memory_order_acquire))
                                                  onAssetDownloaded (name, response);
                                          });

        downloadRequests.push_back (id);
    }
}

void JobClient::onAssetDownloaded (const juce::String& assetName, const ApiClient::Response<juce::File>& response)
{
    if (state != State::Downloading)
        return;

    if (! response.ok())
    {
        const auto downloadError = response.error.value_or (ApiError::transport ("Could not download " + assetName));

        if (isCancellation (downloadError))
            return;

        for (const auto id : downloadRequests)
            api.cancel (id);

        downloadRequests.clear();
        pendingDownloads = 0;
        fail (downloadError);
        return;
    }

    if (--pendingDownloads <= 0)
    {
        downloadRequests.clear();
        pendingDownloads = 0;
        stage = JobStage::Done;
        progress = 1.0;
        setState (State::Ready);
        return;
    }

    const auto total = static_cast<double> (downloadRequests.size());
    progress = total > 0.0 ? juce::jlimit (0.0, 1.0, (total - pendingDownloads) / total) : 0.0;
    sendChangeMessage();
}

bool JobClient::loadResultFromCache (const juce::File& directory)
{
    const auto resultFile = directory.getChildFile ("result.json");

    if (! resultFile.existsAsFile())
        return false;

    auto parsed = JobResult::fromJson (juce::JSON::parse (resultFile.loadFileAsString()));

    if (! parsed.has_value())
        return false;

    for (const auto& stem : parsed->stems)
        if (stem.url.isNotEmpty() && ! directory.getChildFile (stem.name + ".wav").existsAsFile())
            return false;

    if (parsed->midi.url.isNotEmpty() && ! directory.getChildFile ("score.mid").existsAsFile())
        return false;

    inputTruncated = parsed->input.truncated;
    result = std::move (parsed);
    return true;
}

void JobClient::saveResultToCache (const JobResult& jobResult) const
{
    const auto id = jobResult.jobId.isNotEmpty() ? jobResult.jobId : jobId;

    if (id.isEmpty())
        return;

    const auto directory = jobDirectoryFor (cacheRoot, id);
    directory.createDirectory();
    directory.getChildFile ("result.json").replaceWithText (juce::JSON::toString (jobResult.toVar(), true));
}

} // namespace tonamorph::cloud
