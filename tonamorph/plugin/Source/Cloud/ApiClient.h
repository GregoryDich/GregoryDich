#pragma once

/**
 * Asynchronous HTTPS client for the API (docs/API_CONTRACT.md v2).
 *
 * Every call returns immediately with a RequestId and runs on an internal
 * juce::ThreadPool. Completion callbacks are always delivered on the message thread
 * (juce::MessageManager::callAsync); a callback is never invoked after cancel() /
 * cancelAll() / destruction returned for that request, except with a `cancelled` error
 * when the request was already in flight. Requests that fail with 429 or 5xx (or a
 * transport error) are retried with exponential backoff up to Config::maxRetries,
 * honouring `Retry-After` when present. Every request carries `User-Agent`,
 * `X-Plugin-Version` and `X-Host` (the DAW, from juce::PluginHostType).
 */

#include <JuceHeader.h>

#include "Cloud/Models.h"
#include "Core/Strings.h"

#include <atomic>
#include <cstdint>
#include <functional>
#include <map>
#include <memory>
#include <optional>

namespace tonamorph::cloud
{

class ApiClient
{
public:
    /** Client configuration; all fields have production defaults. */
    struct Config
    {
        juce::String baseUrl { "https://api.tonamorph.com" };   ///< no trailing slash; routes are appended as "/v1/..."
        int connectionTimeoutMs = 15000;
        int maxRetries = 3;                                   ///< retries on 429 / 5xx / transport errors
        int initialBackoffMs = 500;                           ///< doubled after each retry, capped at 8 s
        int numThreads = 3;                                   ///< thread-pool size (one stream + parallel downloads)
        juce::String pluginVersion { TONAMORPH_VERSION_STRING };   ///< `X-Plugin-Version`
        juce::String hostName;                                ///< `X-Host`; filled from juce::PluginHostType when empty
        juce::String userAgent { juce::String (strings::productName) + "/" + TONAMORPH_VERSION_STRING };
    };

    /** Handle for cancelling a request; 0 is never issued. */
    using RequestId = std::uint64_t;
    static constexpr RequestId invalidRequest = 0;

    /** Outcome of a request: exactly one of `value` / `error` is set. */
    template <typename T>
    struct Response
    {
        int statusCode = 0;               ///< HTTP status, 0 when no response was received
        std::optional<T> value;           ///< parsed body on success
        std::optional<ApiError> error;    ///< contract §5 error, transport error or cancellation

        bool ok() const noexcept { return value.has_value(); }
    };

    template <typename T>
    using Callback = std::function<void (Response<T>)>;

    /** Transfer progress; `bytesTotal` is -1 when unknown. Called on the message thread. */
    using ProgressCallback = std::function<void (juce::int64 bytesDone, juce::int64 bytesTotal)>;

    /** Production defaults (Config{}). */
    ApiClient();
    explicit ApiClient (Config config);
    /** Cancels all requests and waits for the pool to drain. */
    ~ApiClient();

    //==============================================================================
    void setBaseUrl (const juce::String& baseUrl);
    juce::String getBaseUrl() const;
    const Config& getConfig() const noexcept { return config; }

    /** Sets the JWT sent as `Authorization: Bearer`; empty clears it. Thread-safe. */
    void setAccessToken (const juce::String& accessToken);
    /** Sets the `X-API-Key` used when no access token is set (contract §11). Thread-safe. */
    void setApiKey (const juce::String& apiKey);
    void clearCredentials();
    bool hasCredentials() const;

    //==============================================================================
    /** POST /v1/auth/token. */
    RequestId login (const juce::String& email, const juce::String& password, Callback<AuthTokens> onDone);
    /** POST /v1/auth/refresh. */
    RequestId refresh (const juce::String& refreshToken, Callback<AuthTokens> onDone);
    /** GET /v1/me. */
    RequestId getMe (Callback<MeResponse> onDone);
    /** GET /v1/plans (authenticated when credentials are set, so checkout URLs carry the user id). */
    RequestId getPlans (Callback<std::vector<PlanInfo>> onDone);

    /** POST /v1/jobs (multipart: `audio` file part + `options` JSON field).
        @param audioData   encoded audio (FLAC from UploadEncoder), <= 10 MB
        @param fileName    file name for the part, e.g. "input.flac"
        @param mimeType    e.g. "audio/flac"
        @param uploadProgress optional upload progress */
    RequestId submitJob (const juce::MemoryBlock& audioData, const juce::String& fileName,
                         const juce::String& mimeType, const JobOptions& options,
                         Callback<JobSubmitResponse> onDone, ProgressCallback uploadProgress = {});
    /** GET /v1/jobs/{jobId}. */
    RequestId getJob (const juce::String& jobId, Callback<JobStatus> onDone);
    /** DELETE /v1/jobs/{jobId}; value = true on 2xx. */
    RequestId cancelJob (const juce::String& jobId, Callback<bool> onDone);
    /** GET /v1/jobs/{jobId}/events as Server-Sent Events. `onEvent` fires for every
        progress/result/error event; `onFinished` fires once when a `result` or `error`
        event ends the stream (value = final JobStatus), or with an error when the
        connection drops / is cancelled. Heartbeat comments are ignored. Not retried
        after the first event was delivered. */
    RequestId streamJobEvents (const juce::String& jobId,
                               std::function<void (const JobEvent&)> onEvent,
                               Callback<JobStatus> onFinished);
    /** POST /v1/api-keys (contract §11). */
    RequestId createApiKey (const juce::String& name, Callback<ApiKeyInfo> onDone);
    /** POST /v1/jobs/{jobId}/feedback with a body from core::buildFeedbackJson (GTM B §5).
        A 404 (route not deployed yet) is reported as an error like any other status. */
    RequestId submitFeedback (const juce::String& jobId, const juce::String& jsonBody, Callback<FeedbackResponse> onDone);
    /** POST /v1/nps with a body from core::buildNpsJson (GTM B §5). A second answer within
        30 days is a 409, reported as an error with that status. */
    RequestId postNps (const juce::String& jsonBody, Callback<NpsResponse> onDone);
    /** GET /v1/version (public, no credentials sent). */
    RequestId getVersion (Callback<VersionInfo> onDone);
    /** POST /v1/telemetry/crash with a body from core::buildCrashReportJson; anonymous, so
        no credentials are sent. value = true on 2xx. */
    RequestId postCrashReport (const juce::String& jsonBody, Callback<bool> onDone);
    /** Downloads a signed URL to `destination` (parent directory created, partial file
        removed on failure). No auth headers are sent. value = `destination` on success. */
    RequestId downloadFile (const juce::URL& url, const juce::File& destination,
                            Callback<juce::File> onDone, ProgressCallback progress = {});

    //==============================================================================
    /** Cancels one request; its callback receives `ApiError::cancelled()` if still pending. */
    void cancel (RequestId id);
    /** Cancels every request. Safe to call from the message thread only. */
    void cancelAll();
    int getNumPendingRequests() const;
    bool isBusy() const { return getNumPendingRequests() > 0; }

private:
    /** Per-request shared state: cancellation flag polled by the worker between reads. */
    struct RequestContext
    {
        RequestId id = invalidRequest;
        std::atomic<bool> cancelled { false };
    };

    class Job;   // juce::ThreadPoolJob running one request

    /** Registers a context, schedules `work` on the pool and returns the new id. */
    RequestId enqueue (const juce::String& name, std::function<void (RequestContext&)> work);
    /** Removes a finished request from the pending map. */
    void finish (RequestId id);
    /** Delivers `fn` on the message thread unless the request was cancelled meanwhile. */
    void deliver (RequestId id, std::function<void()> fn);
    /** Builds the `Authorization` / `X-API-Key` / `User-Agent` header block. */
    juce::String buildHeaders (bool includeAuth, const juce::String& extra = {}) const;
    /** Absolute URL for a versioned route such as "/v1/me". */
    juce::URL makeUrl (const juce::String& route) const;

    Config config;
    mutable juce::CriticalSection configLock;
    juce::String accessToken;
    juce::String apiKey;

    juce::ThreadPool pool;
    std::atomic<RequestId> nextRequestId { 1 };
    mutable juce::CriticalSection pendingLock;
    std::map<RequestId, std::shared_ptr<RequestContext>> pending;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR (ApiClient)
};

} // namespace tonamorph::cloud
