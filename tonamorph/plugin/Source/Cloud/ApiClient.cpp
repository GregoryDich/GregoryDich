#include "Cloud/ApiClient.h"

#include "Cloud/RetryPolicy.h"
#include "Cloud/SseParser.h"
#include "Core/Strings.h"

#include <memory>
#include <utility>

namespace tonamorph::cloud
{

namespace
{

constexpr int bulkReadChunkBytes = 16384;
/** SSE is read byte-wise: juce::WebInputStream::read blocks until the requested number of
    bytes arrived, so a larger chunk would stall until the next events filled it. */
constexpr int streamReadChunkBytes = 1;
constexpr int cancelPollSliceMs = 50;
constexpr int numRedirectsToFollow = 5;

/** Outcome of a single HTTP attempt. */
struct HttpResult
{
    int statusCode = 0;
    juce::MemoryBlock body;
    juce::StringPairArray responseHeaders;
    juce::int64 totalLength = -1;
    bool cancelled = false;
    juce::String transportMessage;   ///< set when no response was received at all

    bool isTransportFailure() const noexcept { return transportMessage.isNotEmpty(); }
    bool isSuccess() const noexcept
    {
        return ! cancelled && ! isTransportFailure() && statusCode >= 200 && statusCode < 300;
    }
};

/** Consumes a block of the response body; returning false stops reading. */
using ChunkHandler = std::function<bool (const char* data, int numBytes, juce::int64 bytesSoFar, juce::int64 totalBytes)>;

/** Bridges POST upload progress and aborts the transfer once the request is cancelled. */
class UploadListener final : public juce::WebInputStream::Listener
{
public:
    UploadListener (const std::atomic<bool>& cancelledFlag, std::function<void (juce::int64, juce::int64)> onProgress)
        : cancelled (cancelledFlag), progress (std::move (onProgress))
    {
    }

    bool postDataSendProgress (juce::WebInputStream&, int bytesSent, int totalBytes) override
    {
        if (cancelled.load (std::memory_order_acquire))
            return false;

        if (progress != nullptr)
            progress (static_cast<juce::int64> (bytesSent), static_cast<juce::int64> (totalBytes));

        return true;
    }

private:
    const std::atomic<bool>& cancelled;
    std::function<void (juce::int64, juce::int64)> progress;
};

juce::String bodyToString (const juce::MemoryBlock& body)
{
    return body.getSize() > 0 ? juce::String::fromUTF8 (static_cast<const char*> (body.getData()),
                                                        static_cast<int> (body.getSize()))
                              : juce::String();
}

/** Runs one request. When `onChunk` is null the body is collected into the result. */
HttpResult performOnce (const juce::URL& url, const juce::String& method, const juce::String& extraHeaders,
                        int timeoutMs, bool parametersInBody, const std::atomic<bool>& cancelled,
                        juce::WebInputStream::Listener* listener, const ChunkHandler& onChunk,
                        int chunkBytes = bulkReadChunkBytes)
{
    HttpResult result;

    if (cancelled.load (std::memory_order_acquire))
    {
        result.cancelled = true;
        return result;
    }

    juce::WebInputStream stream (url, parametersInBody);
    stream.withExtraHeaders (extraHeaders)
          .withConnectionTimeout (timeoutMs)
          .withNumRedirectsToFollow (numRedirectsToFollow)
          .withCustomRequestCommand (method);

    const bool connected = stream.connect (listener);
    result.statusCode = stream.getStatusCode();
    result.responseHeaders = stream.getResponseHeaders();
    result.totalLength = stream.getTotalLength();

    if (cancelled.load (std::memory_order_acquire))
    {
        result.cancelled = true;
        return result;
    }

    if (! connected && result.statusCode == 0)
    {
        result.transportMessage = juce::String::fromUTF8 (strings::serviceUnreachable);
        return result;
    }

    juce::HeapBlock<char> buffer (static_cast<size_t> (juce::jmax (1, chunkBytes)));
    juce::MemoryBlock collected;
    juce::int64 bytesSoFar = 0;

    {
        juce::MemoryOutputStream collector (collected, false);

        for (;;)
        {
            if (cancelled.load (std::memory_order_acquire))
            {
                result.cancelled = true;
                break;
            }

            const int numRead = stream.read (buffer.get(), juce::jmax (1, chunkBytes));

            if (numRead <= 0)
                break;

            bytesSoFar += numRead;

            if (onChunk != nullptr)
            {
                if (! onChunk (buffer.get(), numRead, bytesSoFar, result.totalLength))
                    break;
            }
            else
            {
                collector.write (buffer.get(), static_cast<size_t> (numRead));
            }
        }

        collector.flush();
    }

    result.body = std::move (collected);
    return result;
}

/** Waits `delayMs`, polling the cancellation flag; false when the request was cancelled. */
bool waitBeforeRetry (int delayMs, const std::atomic<bool>& cancelled)
{
    for (int waited = 0; waited < delayMs; waited += cancelPollSliceMs)
    {
        if (cancelled.load (std::memory_order_acquire))
            return false;

        juce::Thread::sleep (juce::jmin (cancelPollSliceMs, delayMs - waited));
    }

    return ! cancelled.load (std::memory_order_acquire);
}

int retryAfterMsFrom (const juce::StringPairArray& headers)
{
    const auto value = headers.getValue ("Retry-After", {}).toStdString();
    return retry::parseRetryAfterMs (value);
}

/** Contract §5: rate limiting and transient upstream failures are worth another attempt. */
bool shouldRetry (const HttpResult& http, int attempt, int maxRetries)
{
    if (http.cancelled || attempt >= maxRetries)
        return false;

    return http.isTransportFailure() || retry::isRetryableStatus (http.statusCode);
}

/** Runs a request with the configured backoff schedule. */
HttpResult performWithRetries (const juce::URL& url, const juce::String& method, const juce::String& extraHeaders,
                               const ApiClient::Config& config, bool parametersInBody,
                               const std::atomic<bool>& cancelled, juce::WebInputStream::Listener* listener,
                               const ChunkHandler& onChunk, int chunkBytes = bulkReadChunkBytes)
{
    HttpResult http;

    for (int attempt = 0;; ++attempt)
    {
        http = performOnce (url, method, extraHeaders, config.connectionTimeoutMs, parametersInBody,
                            cancelled, listener, onChunk, chunkBytes);

        if (! shouldRetry (http, attempt, config.maxRetries))
            break;

        const auto delay = retry::backoffDelayMs (attempt, config.initialBackoffMs,
                                                  juce::Random::getSystemRandom().nextDouble(),
                                                  retryAfterMsFrom (http.responseHeaders));

        if (! waitBeforeRetry (delay, cancelled))
        {
            http.cancelled = true;
            break;
        }
    }

    return http;
}

ApiError invalidResponseError (int statusCode)
{
    ApiError error;
    error.code = "invalid_response";
    error.message = "The server returned an unexpected response";
    error.httpStatus = statusCode;
    return error;
}

/** Turns an attempt into a Response<T>; `extract` is only consulted on a 2xx. */
template <typename T, typename Extract>
ApiClient::Response<T> makeResponse (const HttpResult& http, Extract&& extract)
{
    ApiClient::Response<T> response;
    response.statusCode = http.statusCode;

    if (http.cancelled)
        response.error = ApiError::cancelled();
    else if (http.isTransportFailure())
        response.error = ApiError::transport (http.transportMessage);
    else if (! http.isSuccess())
        response.error = ApiError::fromHttpStatus (http.statusCode, bodyToString (http.body));
    else if (auto value = extract (http))
        response.value = std::move (value);
    else
        response.error = invalidResponseError (http.statusCode);

    return response;
}

/** Parses the body as JSON and hands it to a model's fromJson(). */
template <typename T, typename Parse>
auto jsonExtractor (Parse parse)
{
    return [parse] (const HttpResult& http) -> std::optional<T>
    {
        juce::var parsed;

        if (! juce::JSON::parse (bodyToString (http.body), parsed).wasOk())
            return std::nullopt;

        return parse (parsed);
    };
}

/** Delivers a finished response: cancellations bypass the client's cancelled-request
    filter so the caller always learns why its request stopped. */
template <typename T, typename Deliver>
void deliverResponse (ApiClient::Callback<T> onDone, ApiClient::Response<T> response, Deliver&& deliverFn)
{
    if (onDone == nullptr)
        return;

    const bool wasCancelled = response.error.has_value() && response.error->code == "cancelled";
    auto invoke = [onDone = std::move (onDone), response = std::move (response)] { onDone (response); };

    if (wasCancelled)
        juce::MessageManager::callAsync (std::move (invoke));
    else
        deliverFn (std::move (invoke));
}

/** Header values must be one line of printable ASCII; anything else is dropped. */
juce::String sanitiseHeaderValue (const juce::String& value, int maxLength = 64)
{
    juce::String clean;

    for (const auto c : value)
        if (c >= 0x20 && c <= 0x7e)
            clean << static_cast<juce::juce_wchar> (c);

    return clean.trim().substring (0, maxLength);
}

juce::var makeJsonBody (const std::initializer_list<std::pair<const char*, juce::var>> fields)
{
    juce::DynamicObject::Ptr object (new juce::DynamicObject());

    for (const auto& [key, value] : fields)
        object->setProperty (juce::Identifier (key), value);

    return juce::var (object.get());
}

} // namespace

//==============================================================================
/** One request on the thread pool; `work` polls `context.cancelled` between blocking reads. */
class ApiClient::Job final : public juce::ThreadPoolJob
{
public:
    Job (ApiClient& ownerToUse, std::shared_ptr<RequestContext> contextToUse,
         const juce::String& name, std::function<void (RequestContext&)> workToRun)
        : juce::ThreadPoolJob (name),
          owner (ownerToUse),
          context (std::move (contextToUse)),
          work (std::move (workToRun))
    {
    }

    JobStatus runJob() override
    {
        if (! context->cancelled.load (std::memory_order_acquire))
            work (*context);

        owner.finish (context->id);
        return jobHasFinished;
    }

private:
    ApiClient& owner;
    std::shared_ptr<RequestContext> context;
    std::function<void (RequestContext&)> work;
};

//==============================================================================
ApiClient::ApiClient()
    : ApiClient (Config{})
{
}

ApiClient::ApiClient (Config configToUse)
    : config (std::move (configToUse)),
      pool (juce::ThreadPoolOptions{}.withThreadName (juce::String (strings::productName) + " API")
                                     .withNumberOfThreads (juce::jmax (1, config.numThreads)))
{
    config.pluginVersion = sanitiseHeaderValue (config.pluginVersion);

    if (config.hostName.isEmpty())
        config.hostName = juce::PluginHostType().getHostDescription();

    config.hostName = sanitiseHeaderValue (config.hostName);
}

ApiClient::~ApiClient()
{
    cancelAll();
    pool.removeAllJobs (true, 10000);
}

void ApiClient::setBaseUrl (const juce::String& baseUrl)
{
    const juce::ScopedLock lock (configLock);
    config.baseUrl = baseUrl.trimCharactersAtEnd ("/");
}

juce::String ApiClient::getBaseUrl() const
{
    const juce::ScopedLock lock (configLock);
    return config.baseUrl;
}

void ApiClient::setAccessToken (const juce::String& token)
{
    const juce::ScopedLock lock (configLock);
    accessToken = token;
}

void ApiClient::setApiKey (const juce::String& key)
{
    const juce::ScopedLock lock (configLock);
    apiKey = key;
}

void ApiClient::clearCredentials()
{
    const juce::ScopedLock lock (configLock);
    accessToken.clear();
    apiKey.clear();
}

bool ApiClient::hasCredentials() const
{
    const juce::ScopedLock lock (configLock);
    return accessToken.isNotEmpty() || apiKey.isNotEmpty();
}

//==============================================================================
ApiClient::RequestId ApiClient::login (const juce::String& email, const juce::String& password, Callback<AuthTokens> onDone)
{
    const auto body = juce::JSON::toString (makeJsonBody ({ { "email", email }, { "password", password } }), true);

    return enqueue ("POST /v1/auth/token", [this, body, onDone = std::move (onDone)] (RequestContext& context)
    {
        const auto url = makeUrl ("/v1/auth/token").withPOSTData (body);
        const auto headers = buildHeaders (false, "Content-Type: application/json\r\n");
        const auto http = performWithRetries (url, "POST", headers, getConfig(), false, context.cancelled, nullptr, {});

        deliverResponse (onDone, makeResponse<AuthTokens> (http, jsonExtractor<AuthTokens> (&AuthTokens::fromJson)),
                         [this, id = context.id] (std::function<void()> fn) { deliver (id, std::move (fn)); });
    });
}

ApiClient::RequestId ApiClient::refresh (const juce::String& refreshToken, Callback<AuthTokens> onDone)
{
    const auto body = juce::JSON::toString (makeJsonBody ({ { "refresh_token", refreshToken } }), true);

    return enqueue ("POST /v1/auth/refresh", [this, body, onDone = std::move (onDone)] (RequestContext& context)
    {
        const auto url = makeUrl ("/v1/auth/refresh").withPOSTData (body);
        const auto headers = buildHeaders (false, "Content-Type: application/json\r\n");
        const auto http = performWithRetries (url, "POST", headers, getConfig(), false, context.cancelled, nullptr, {});

        deliverResponse (onDone, makeResponse<AuthTokens> (http, jsonExtractor<AuthTokens> (&AuthTokens::fromJson)),
                         [this, id = context.id] (std::function<void()> fn) { deliver (id, std::move (fn)); });
    });
}

ApiClient::RequestId ApiClient::getMe (Callback<MeResponse> onDone)
{
    return enqueue ("GET /v1/me", [this, onDone = std::move (onDone)] (RequestContext& context)
    {
        const auto http = performWithRetries (makeUrl ("/v1/me"), "GET", buildHeaders (true), getConfig(),
                                              false, context.cancelled, nullptr, {});

        deliverResponse (onDone, makeResponse<MeResponse> (http, jsonExtractor<MeResponse> (&MeResponse::fromJson)),
                         [this, id = context.id] (std::function<void()> fn) { deliver (id, std::move (fn)); });
    });
}

ApiClient::RequestId ApiClient::getPlans (Callback<std::vector<PlanInfo>> onDone)
{
    return enqueue ("GET /v1/plans", [this, onDone = std::move (onDone)] (RequestContext& context)
    {
        const auto http = performWithRetries (makeUrl ("/v1/plans"), "GET", buildHeaders (true), getConfig(),
                                              false, context.cancelled, nullptr, {});

        using Plans = std::vector<PlanInfo>;
        deliverResponse (onDone, makeResponse<Plans> (http, jsonExtractor<Plans> (&PlanInfo::listFromJson)),
                         [this, id = context.id] (std::function<void()> fn) { deliver (id, std::move (fn)); });
    });
}

ApiClient::RequestId ApiClient::submitJob (const juce::MemoryBlock& audioData, const juce::String& fileName,
                                           const juce::String& mimeType, const JobOptions& options,
                                           Callback<JobSubmitResponse> onDone, ProgressCallback uploadProgress)
{
    const auto optionsJson = options.toJsonString();

    return enqueue ("POST /v1/jobs", [this, audioData, fileName, mimeType, optionsJson,
                                      onDone = std::move (onDone), uploadProgress = std::move (uploadProgress)] (RequestContext& context)
    {
        auto deliverFn = [this, id = context.id] (std::function<void()> fn) { deliver (id, std::move (fn)); };

        // Contract §2: the `audio` file part plus the `options` JSON text field. The stream is
        // built with parameters-in-body so `options` becomes a form field, not a query string.
        const auto url = makeUrl ("/v1/jobs")
                             .withDataToUpload ("audio", fileName, audioData, mimeType)
                             .withParameter ("options", optionsJson);

        UploadListener listener (context.cancelled, [&deliverFn, uploadProgress] (juce::int64 sent, juce::int64 total)
        {
            if (uploadProgress != nullptr)
                deliverFn ([uploadProgress, sent, total] { uploadProgress (sent, total); });
        });

        const auto http = performWithRetries (url, "POST", buildHeaders (true), getConfig(), true,
                                              context.cancelled, &listener, {});

        deliverResponse (onDone, makeResponse<JobSubmitResponse> (http, jsonExtractor<JobSubmitResponse> (&JobSubmitResponse::fromJson)),
                         deliverFn);
    });
}

ApiClient::RequestId ApiClient::getJob (const juce::String& jobId, Callback<JobStatus> onDone)
{
    const auto route = "/v1/jobs/" + juce::URL::addEscapeChars (jobId, false);

    return enqueue ("GET " + route, [this, route, onDone = std::move (onDone)] (RequestContext& context)
    {
        const auto http = performWithRetries (makeUrl (route), "GET", buildHeaders (true), getConfig(),
                                              false, context.cancelled, nullptr, {});

        deliverResponse (onDone, makeResponse<JobStatus> (http, jsonExtractor<JobStatus> (&JobStatus::fromJson)),
                         [this, id = context.id] (std::function<void()> fn) { deliver (id, std::move (fn)); });
    });
}

ApiClient::RequestId ApiClient::cancelJob (const juce::String& jobId, Callback<bool> onDone)
{
    const auto route = "/v1/jobs/" + juce::URL::addEscapeChars (jobId, false);

    return enqueue ("DELETE " + route, [this, route, onDone = std::move (onDone)] (RequestContext& context)
    {
        const auto http = performWithRetries (makeUrl (route), "DELETE", buildHeaders (true), getConfig(),
                                              false, context.cancelled, nullptr, {});

        auto response = makeResponse<bool> (http, [] (const HttpResult&) { return std::optional<bool> (true); });

        deliverResponse (onDone, std::move (response),
                         [this, id = context.id] (std::function<void()> fn) { deliver (id, std::move (fn)); });
    });
}

ApiClient::RequestId ApiClient::streamJobEvents (const juce::String& jobId,
                                                 std::function<void (const JobEvent&)> onEvent,
                                                 Callback<JobStatus> onFinished)
{
    const auto route = "/v1/jobs/" + juce::URL::addEscapeChars (jobId, false) + "/events";

    return enqueue ("SSE " + route, [this, route, onEvent = std::move (onEvent),
                                     onFinished = std::move (onFinished)] (RequestContext& context)
    {
        auto deliverFn = [this, id = context.id] (std::function<void()> fn) { deliver (id, std::move (fn)); };

        const auto url = makeUrl (route);
        const auto headers = buildHeaders (true, "Accept: text/event-stream\r\nCache-Control: no-cache\r\n");
        const auto& clientConfig = getConfig();

        std::optional<JobStatus> finalStatus;
        std::optional<ApiError> streamError;
        bool receivedAnyEvent = false;
        HttpResult http;

        for (int attempt = 0;; ++attempt)
        {
            sse::Parser parser;

            auto handleEvent = [&] (const sse::Event& raw)
            {
                juce::var payload;
                const auto text = juce::String::fromUTF8 (raw.data.c_str(), static_cast<int> (raw.data.size()));

                if (! juce::JSON::parse (text, payload).wasOk())
                    return true;

                const auto event = JobEvent::fromSse (juce::String (raw.name), payload);

                if (! event.has_value())
                    return true;

                receivedAnyEvent = true;

                if (onEvent != nullptr)
                    deliverFn ([onEvent, value = *event] { onEvent (value); });

                if (event->type == JobEvent::Type::Result)
                    finalStatus = event->status;
                else if (event->type == JobEvent::Type::Error)
                    streamError = event->error;

                return ! event->endsStream();
            };

            http = performWithRetries (url, "GET", headers, clientConfig, false, context.cancelled, nullptr,
                                       [&] (const char* data, int numBytes, juce::int64, juce::int64)
                                       {
                                           for (const auto& raw : parser.feed (data, static_cast<size_t> (numBytes)))
                                               if (! handleEvent (raw))
                                                   return false;

                                           return true;
                                       },
                                       streamReadChunkBytes);

            // A stream closed mid-event still carries a usable payload; a heartbeat does not.
            if (! finalStatus.has_value() && ! streamError.has_value() && ! http.cancelled)
                if (const auto trailing = parser.finish())
                    handleEvent (*trailing);

            if (finalStatus.has_value() || streamError.has_value() || http.cancelled || receivedAnyEvent)
                break;

            if (! shouldRetry (http, attempt, clientConfig.maxRetries))
                break;

            const auto delay = retry::backoffDelayMs (attempt, clientConfig.initialBackoffMs,
                                                      juce::Random::getSystemRandom().nextDouble(),
                                                      retryAfterMsFrom (http.responseHeaders));

            if (! waitBeforeRetry (delay, context.cancelled))
            {
                http.cancelled = true;
                break;
            }
        }

        Response<JobStatus> response;
        response.statusCode = http.statusCode;

        if (http.cancelled)
            response.error = ApiError::cancelled();
        else if (finalStatus.has_value())
            response.value = std::move (finalStatus);
        else if (streamError.has_value())
            response.error = streamError;
        else if (http.isTransportFailure())
            response.error = ApiError::transport (http.transportMessage);
        else if (! http.isSuccess())
            response.error = ApiError::fromHttpStatus (http.statusCode, bodyToString (http.body));
        else
            response.error = ApiError::transport ("The event stream ended before the job finished");

        deliverResponse (onFinished, std::move (response), deliverFn);
    });
}

ApiClient::RequestId ApiClient::createApiKey (const juce::String& name, Callback<ApiKeyInfo> onDone)
{
    const auto body = juce::JSON::toString (makeJsonBody ({ { "name", name } }), true);

    return enqueue ("POST /v1/api-keys", [this, body, onDone = std::move (onDone)] (RequestContext& context)
    {
        const auto url = makeUrl ("/v1/api-keys").withPOSTData (body);
        const auto headers = buildHeaders (true, "Content-Type: application/json\r\n");
        const auto http = performWithRetries (url, "POST", headers, getConfig(), false, context.cancelled, nullptr, {});

        deliverResponse (onDone, makeResponse<ApiKeyInfo> (http, jsonExtractor<ApiKeyInfo> (&ApiKeyInfo::fromJson)),
                         [this, id = context.id] (std::function<void()> fn) { deliver (id, std::move (fn)); });
    });
}

ApiClient::RequestId ApiClient::submitFeedback (const juce::String& jobId, const juce::String& jsonBody,
                                                Callback<FeedbackResponse> onDone)
{
    const auto route = "/v1/jobs/" + juce::URL::addEscapeChars (jobId, false) + "/feedback";

    return enqueue ("POST " + route, [this, route, jsonBody, onDone = std::move (onDone)] (RequestContext& context)
    {
        const auto url = makeUrl (route).withPOSTData (jsonBody);
        const auto headers = buildHeaders (true, "Content-Type: application/json\r\n");
        const auto http = performWithRetries (url, "POST", headers, getConfig(), false, context.cancelled, nullptr, {});

        deliverResponse (onDone, makeResponse<FeedbackResponse> (http, jsonExtractor<FeedbackResponse> (&FeedbackResponse::fromJson)),
                         [this, id = context.id] (std::function<void()> fn) { deliver (id, std::move (fn)); });
    });
}

ApiClient::RequestId ApiClient::postNps (const juce::String& jsonBody, Callback<NpsResponse> onDone)
{
    return enqueue ("POST /v1/nps", [this, jsonBody, onDone = std::move (onDone)] (RequestContext& context)
    {
        const auto url = makeUrl ("/v1/nps").withPOSTData (jsonBody);
        const auto headers = buildHeaders (true, "Content-Type: application/json\r\n");
        const auto http = performWithRetries (url, "POST", headers, getConfig(), false, context.cancelled, nullptr, {});

        deliverResponse (onDone, makeResponse<NpsResponse> (http, jsonExtractor<NpsResponse> (&NpsResponse::fromJson)),
                         [this, id = context.id] (std::function<void()> fn) { deliver (id, std::move (fn)); });
    });
}

ApiClient::RequestId ApiClient::getVersion (Callback<VersionInfo> onDone)
{
    return enqueue ("GET /v1/version", [this, onDone = std::move (onDone)] (RequestContext& context)
    {
        const auto http = performWithRetries (makeUrl ("/v1/version"), "GET", buildHeaders (false), getConfig(),
                                              false, context.cancelled, nullptr, {});

        deliverResponse (onDone, makeResponse<VersionInfo> (http, jsonExtractor<VersionInfo> (&VersionInfo::fromJson)),
                         [this, id = context.id] (std::function<void()> fn) { deliver (id, std::move (fn)); });
    });
}

ApiClient::RequestId ApiClient::postCrashReport (const juce::String& jsonBody, Callback<bool> onDone)
{
    return enqueue ("POST /v1/telemetry/crash", [this, jsonBody, onDone = std::move (onDone)] (RequestContext& context)
    {
        const auto url = makeUrl ("/v1/telemetry/crash").withPOSTData (jsonBody);
        const auto headers = buildHeaders (false, "Content-Type: application/json\r\n");
        const auto http = performWithRetries (url, "POST", headers, getConfig(), false, context.cancelled, nullptr, {});

        auto response = makeResponse<bool> (http, [] (const HttpResult&) { return std::optional<bool> (true); });

        deliverResponse (onDone, std::move (response),
                         [this, id = context.id] (std::function<void()> fn) { deliver (id, std::move (fn)); });
    });
}

ApiClient::RequestId ApiClient::downloadFile (const juce::URL& url, const juce::File& destination,
                                              Callback<juce::File> onDone, ProgressCallback progress)
{
    return enqueue ("GET " + destination.getFileName(),
                    [this, url, destination, onDone = std::move (onDone), progress = std::move (progress)] (RequestContext& context)
    {
        auto deliverFn = [this, id = context.id] (std::function<void()> fn) { deliver (id, std::move (fn)); };
        const auto& clientConfig = getConfig();
        // Signed URLs (contract §2) carry their own credentials; sending ours would break them.
        const auto headers = buildHeaders (false);

        Response<juce::File> response;
        HttpResult http;
        juce::String writeFailure;

        for (int attempt = 0;; ++attempt)
        {
            destination.getParentDirectory().createDirectory();

            juce::TemporaryFile temp (destination);
            writeFailure.clear();

            {
                std::unique_ptr<juce::FileOutputStream> out (temp.getFile().createOutputStream());

                if (out == nullptr || out->failedToOpen())
                {
                    writeFailure = "Could not write to " + destination.getFullPathName();
                    break;
                }

                http = performOnce (url, "GET", headers, clientConfig.connectionTimeoutMs, false, context.cancelled, nullptr,
                                    [&] (const char* data, int numBytes, juce::int64 soFar, juce::int64 total)
                                    {
                                        if (! out->write (data, static_cast<size_t> (numBytes)))
                                        {
                                            writeFailure = "Could not write to " + destination.getFullPathName();
                                            return false;
                                        }

                                        if (progress != nullptr)
                                            deliverFn ([progress, soFar, total] { progress (soFar, total); });

                                        return true;
                                    });

                out->flush();
            }

            if (http.isSuccess() && writeFailure.isEmpty())
            {
                if (! temp.overwriteTargetFileWithTemporary())
                    writeFailure = "Could not save " + destination.getFullPathName();

                break;
            }

            // The TemporaryFile destructor removes the partial download.
            if (! shouldRetry (http, attempt, clientConfig.maxRetries))
                break;

            const auto delay = retry::backoffDelayMs (attempt, clientConfig.initialBackoffMs,
                                                      juce::Random::getSystemRandom().nextDouble(),
                                                      retryAfterMsFrom (http.responseHeaders));

            if (! waitBeforeRetry (delay, context.cancelled))
            {
                http.cancelled = true;
                break;
            }
        }

        if (writeFailure.isNotEmpty() && ! http.cancelled)
        {
            response.statusCode = http.statusCode;
            response.error = ApiError::transport (writeFailure);
        }
        else
        {
            response = makeResponse<juce::File> (http, [&destination] (const HttpResult&)
            {
                return std::optional<juce::File> (destination);
            });
        }

        deliverResponse (onDone, std::move (response), deliverFn);
    });
}

//==============================================================================
void ApiClient::cancel (RequestId id)
{
    std::shared_ptr<RequestContext> context;

    {
        const juce::ScopedLock lock (pendingLock);

        if (const auto it = pending.find (id); it != pending.end())
            context = it->second;
    }

    if (context != nullptr)
        context->cancelled.store (true, std::memory_order_release);
}

void ApiClient::cancelAll()
{
    const juce::ScopedLock lock (pendingLock);

    for (auto& [id, context] : pending)
        context->cancelled.store (true, std::memory_order_release);
}

int ApiClient::getNumPendingRequests() const
{
    const juce::ScopedLock lock (pendingLock);
    return static_cast<int> (pending.size());
}

//==============================================================================
ApiClient::RequestId ApiClient::enqueue (const juce::String& name, std::function<void (RequestContext&)> work)
{
    auto context = std::make_shared<RequestContext>();
    context->id = nextRequestId.fetch_add (1, std::memory_order_relaxed);

    {
        const juce::ScopedLock lock (pendingLock);
        pending[context->id] = context;
    }

    pool.addJob (new Job (*this, context, name, std::move (work)), true);
    return context->id;
}

void ApiClient::finish (RequestId id)
{
    const juce::ScopedLock lock (pendingLock);
    pending.erase (id);
}

void ApiClient::deliver (RequestId id, std::function<void()> fn)
{
    std::shared_ptr<RequestContext> context;

    {
        const juce::ScopedLock lock (pendingLock);

        if (const auto it = pending.find (id); it != pending.end())
            context = it->second;
    }

    if (context != nullptr && context->cancelled.load (std::memory_order_acquire))
        return;

    juce::MessageManager::callAsync ([context, fn = std::move (fn)]
    {
        if (context != nullptr && context->cancelled.load (std::memory_order_acquire))
            return;

        fn();
    });
}

juce::String ApiClient::buildHeaders (bool includeAuth, const juce::String& extra) const
{
    juce::String headers;

    {
        const juce::ScopedLock lock (configLock);

        if (includeAuth)
        {
            if (accessToken.isNotEmpty())
                headers << "Authorization: Bearer " << accessToken << "\r\n";
            else if (apiKey.isNotEmpty())
                headers << "X-API-Key: " << apiKey << "\r\n";
        }

        headers << "User-Agent: " << config.userAgent << "\r\n";

        if (config.pluginVersion.isNotEmpty())
            headers << "X-Plugin-Version: " << config.pluginVersion << "\r\n";

        if (config.hostName.isNotEmpty())
            headers << "X-Host: " << config.hostName << "\r\n";
    }

    if (! extra.containsIgnoreCase ("Accept:"))
        headers << "Accept: application/json\r\n";

    headers << extra;
    return headers;
}

juce::URL ApiClient::makeUrl (const juce::String& route) const
{
    return juce::URL (getBaseUrl() + route);
}

} // namespace tonamorph::cloud
