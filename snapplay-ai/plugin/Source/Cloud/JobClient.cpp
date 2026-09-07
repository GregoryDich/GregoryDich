#include "Cloud/JobClient.h"

namespace snapplay::cloud
{

JobClient::JobClient (ApiClient& client, AuthManager& authToUse, juce::File cacheRootToUse)
    : api (client),
      auth (authToUse),
      cacheRoot (std::move (cacheRootToUse)),
      encodePool (juce::ThreadPoolOptions{}.withThreadName ("SnapPlay Encoder").withNumberOfThreads (1))
{
}

JobClient::~JobClient()
{
    encodePool.removeAllJobs (true, 5000);
}

juce::File JobClient::defaultCacheRoot()
{
    return juce::File::getSpecialLocation (juce::File::userApplicationDataDirectory)
               .getChildFile ("SnapPlay")
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
    juce::ignoreUnused (audioFile, options);
}

void JobClient::submitBuffer (const juce::AudioBuffer<float>& audio, double sampleRate, JobOptions options)
{
    juce::ignoreUnused (audio, sampleRate, options);
}

void JobClient::loadCachedJob (const juce::String& jobIdToLoad)
{
    juce::ignoreUnused (jobIdToLoad);
}

void JobClient::cancel()
{
}

void JobClient::reset()
{
    jobId.clear();
    result.reset();
    error.reset();
    inputTruncated = false;
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
    return toString (state);
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

void JobClient::startEncoding (std::function<UploadEncoder::Result()> encode, JobOptions options)
{
    juce::ignoreUnused (encode, options);
}

void JobClient::onEncoded (const UploadEncoder::Result& encoded, const JobOptions& options)
{
    juce::ignoreUnused (encoded, options);
}

void JobClient::submit (const juce::MemoryBlock& flacData, const JobOptions& options)
{
    juce::ignoreUnused (flacData, options);
}

void JobClient::onSubmitted (const JobSubmitResponse& response)
{
    juce::ignoreUnused (response);
}

void JobClient::streamEvents()
{
}

void JobClient::onEvent (const JobEvent& event)
{
    juce::ignoreUnused (event);
}

void JobClient::onStreamFinished (const ApiClient::Response<JobStatus>& finalStatus)
{
    juce::ignoreUnused (finalStatus);
}

void JobClient::downloadAssets (const JobResult& jobResult)
{
    juce::ignoreUnused (jobResult);
}

void JobClient::onAssetDownloaded (const juce::String& assetName, const ApiClient::Response<juce::File>& response)
{
    juce::ignoreUnused (assetName, response);
}

bool JobClient::loadResultFromCache (const juce::File& directory)
{
    juce::ignoreUnused (directory);
    return false;
}

void JobClient::saveResultToCache (const JobResult& jobResult) const
{
    juce::ignoreUnused (jobResult);
}

} // namespace snapplay::cloud
