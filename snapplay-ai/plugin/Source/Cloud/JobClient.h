#pragma once

/**
 * Drives one audio → stems + MIDI job end to end (contract §2):
 *
 *   Idle → Encoding → Submitting → Queued → Running → Downloading → Ready
 *                                    ↘ Failed / Cancelled at any point
 *
 * Encoding runs on a private worker thread; network stages run on the ApiClient pool;
 * every state change is published on the message thread via juce::ChangeBroadcaster.
 * Results and downloaded assets are cached per job under `<cacheRoot>/<jobId>/`
 * (`result.json`, `<stem>.wav`, `score.mid`) so a job can be reloaded without spending a
 * credit. All public methods must be called on the message thread.
 */

#include <JuceHeader.h>

#include "Cloud/ApiClient.h"
#include "Cloud/AuthManager.h"
#include "Cloud/Models.h"
#include "Cloud/UploadEncoder.h"

#include <atomic>
#include <memory>
#include <optional>

namespace snapplay::cloud
{

class JobClient : public juce::ChangeBroadcaster
{
public:
    enum class State { Idle, Encoding, Submitting, Queued, Running, Downloading, Ready, Failed, Cancelled };

    JobClient (ApiClient& client, AuthManager& auth, juce::File cacheRoot = defaultCacheRoot());
    ~JobClient() override;

    /** `<user app data>/SnapPlay/jobs`. */
    static juce::File defaultCacheRoot();
    static juce::String toString (State state);

    //==============================================================================
    /** Encodes `audioFile` (UploadEncoder), submits it and follows the job to Ready.
        Fails immediately with `insufficient_credits` when the known balance is 0. */
    void submitFile (const juce::File& audioFile, JobOptions options);
    /** Same as submitFile() for an in-memory buffer. */
    void submitBuffer (const juce::AudioBuffer<float>& audio, double sampleRate, JobOptions options);
    /** Reloads a previous job without a credit charge: uses the cached `result.json` and
        assets when present, otherwise GET /v1/jobs/{id} and downloads if the URLs have
        not expired. Ends in Ready or Failed. */
    void loadCachedJob (const juce::String& jobId);
    /** Cancels the current job (DELETE /v1/jobs/{id} while queued, otherwise stops
        streaming/downloads) and ends in Cancelled. */
    void cancel();
    /** Returns to Idle and forgets the current job; the cache is kept. */
    void reset();

    //==============================================================================
    State getState() const noexcept { return state; }
    bool isRunning() const noexcept;
    bool isReady() const noexcept { return state == State::Ready; }
    JobStage getStage() const noexcept { return stage; }
    /** 0..1 within the current stage, as reported by the server. */
    double getProgress() const noexcept { return progress; }
    /** Human-readable line for the UI, e.g. "Separating stems… 35 %". */
    juce::String getStatusMessage() const;

    juce::String getJobId() const { return jobId; }
    const std::optional<JobResult>& getResult() const noexcept { return result; }
    std::optional<ApiError> getError() const { return error; }
    /** True when the encoder or the server truncated the input to 60 s. */
    bool wasInputTruncated() const noexcept { return inputTruncated; }

    //==============================================================================
    juce::File getCacheRoot() const { return cacheRoot; }
    void setCacheRoot (const juce::File& newRoot);
    /** `<cacheRoot>/<jobId>` for the current job (may not exist yet). */
    juce::File getJobDirectory() const;
    static juce::File jobDirectoryFor (const juce::File& cacheRoot, const juce::String& jobId);
    /** Local WAV for a stem name; exists only when state is Ready. */
    juce::File getStemFile (const juce::String& stemName) const;
    juce::File getMidiFile() const;
    juce::File getResultFile() const;
    /** Deletes every cached job directory. */
    void clearCache();

private:
    void setState (State newState);
    void fail (const ApiError& apiError);
    /** Clears the previous job and checks the known credit balance; false when the
        submission was refused (the client is then already in Failed). */
    bool beginSubmission();
    void startEncoding (std::function<UploadEncoder::Result()> encode, JobOptions options);
    void onEncoded (const UploadEncoder::Result& encoded, const JobOptions& options);
    void submit (const juce::MemoryBlock& flacData, const JobOptions& options);
    void onSubmitted (const JobSubmitResponse& response);
    void streamEvents();
    void onEvent (const JobEvent& event);
    void onStreamFinished (const ApiClient::Response<JobStatus>& finalStatus);
    void downloadAssets (const JobResult& jobResult);
    void onAssetDownloaded (const juce::String& assetName, const ApiClient::Response<juce::File>& response);
    bool loadResultFromCache (const juce::File& directory);
    void saveResultToCache (const JobResult& jobResult) const;

    ApiClient& api;
    AuthManager& auth;
    juce::File cacheRoot;
    juce::ThreadPool encodePool;

    State state = State::Idle;
    JobStage stage = JobStage::Upload;
    double progress = 0.0;
    juce::String jobId;
    std::optional<JobResult> result;
    std::optional<ApiError> error;
    bool inputTruncated = false;

    ApiClient::RequestId activeRequest = ApiClient::invalidRequest;
    std::vector<ApiClient::RequestId> downloadRequests;
    int pendingDownloads = 0;

    /** Cleared by the destructor and shared with every asynchronous continuation, so an
        encode or a poll that is already queued for the message thread cannot touch a
        destroyed client. */
    std::shared_ptr<std::atomic<bool>> lifetime { std::make_shared<std::atomic<bool>> (true) };

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR (JobClient)
};

} // namespace snapplay::cloud
