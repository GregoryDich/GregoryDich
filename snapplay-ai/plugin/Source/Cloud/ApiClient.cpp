#include "Cloud/ApiClient.h"

namespace snapplay::cloud
{

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
      pool (juce::ThreadPoolOptions{}.withThreadName ("SnapPlay API")
                                     .withNumberOfThreads (juce::jmax (1, config.numThreads)))
{
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
    juce::ignoreUnused (email, password, onDone);
    return invalidRequest;
}

ApiClient::RequestId ApiClient::refresh (const juce::String& refreshToken, Callback<AuthTokens> onDone)
{
    juce::ignoreUnused (refreshToken, onDone);
    return invalidRequest;
}

ApiClient::RequestId ApiClient::getMe (Callback<MeResponse> onDone)
{
    juce::ignoreUnused (onDone);
    return invalidRequest;
}

ApiClient::RequestId ApiClient::getPlans (Callback<std::vector<PlanInfo>> onDone)
{
    juce::ignoreUnused (onDone);
    return invalidRequest;
}

ApiClient::RequestId ApiClient::submitJob (const juce::MemoryBlock& audioData, const juce::String& fileName,
                                           const juce::String& mimeType, const JobOptions& options,
                                           Callback<JobSubmitResponse> onDone, ProgressCallback uploadProgress)
{
    juce::ignoreUnused (audioData, fileName, mimeType, options, onDone, uploadProgress);
    return invalidRequest;
}

ApiClient::RequestId ApiClient::getJob (const juce::String& jobId, Callback<JobStatus> onDone)
{
    juce::ignoreUnused (jobId, onDone);
    return invalidRequest;
}

ApiClient::RequestId ApiClient::cancelJob (const juce::String& jobId, Callback<bool> onDone)
{
    juce::ignoreUnused (jobId, onDone);
    return invalidRequest;
}

ApiClient::RequestId ApiClient::streamJobEvents (const juce::String& jobId,
                                                 std::function<void (const JobEvent&)> onEvent,
                                                 Callback<JobStatus> onFinished)
{
    juce::ignoreUnused (jobId, onEvent, onFinished);
    return invalidRequest;
}

ApiClient::RequestId ApiClient::createApiKey (const juce::String& name, Callback<ApiKeyInfo> onDone)
{
    juce::ignoreUnused (name, onDone);
    return invalidRequest;
}

ApiClient::RequestId ApiClient::downloadFile (const juce::URL& url, const juce::File& destination,
                                              Callback<juce::File> onDone, ProgressCallback progress)
{
    juce::ignoreUnused (url, destination, onDone, progress);
    return invalidRequest;
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
    juce::ignoreUnused (id);
    juce::MessageManager::callAsync (std::move (fn));
}

juce::String ApiClient::buildHeaders (bool includeAuth, const juce::String& extra) const
{
    juce::ignoreUnused (includeAuth, extra);
    return {};
}

juce::URL ApiClient::makeUrl (const juce::String& route) const
{
    return juce::URL (getBaseUrl() + route);
}

} // namespace snapplay::cloud
