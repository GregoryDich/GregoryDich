#include "Cloud/AuthManager.h"

#include <utility>

namespace tonamorph::cloud
{

namespace
{

// Storage keys. Only tokens and identifiers are persisted; nothing is ever logged.
constexpr const char* keyAccessToken  = "auth.accessToken";
constexpr const char* keyRefreshToken = "auth.refreshToken";
constexpr const char* keyExpiresAtMs  = "auth.expiresAtMs";
constexpr const char* keyUserId       = "auth.userId";
constexpr const char* keyUserEmail    = "auth.userEmail";
constexpr const char* keyUserPlan     = "auth.userPlan";
constexpr const char* keyApiKey       = "auth.apiKey";

/** How often the timer looks at the token while signed in and not polling. */
constexpr int tokenCheckIntervalMs = 30000;
/** Refresh this long before the access token actually expires. */
constexpr int tokenRefreshMarginSeconds = 120;
constexpr int minPollIntervalMs = 1000;

ApiError fallbackError (const std::optional<ApiError>& error, const juce::String& message)
{
    return error.value_or (ApiError::transport (message));
}

} // namespace

//==============================================================================
AuthManager::AuthManager (ApiClient& client)
    : AuthManager (client, defaultStorageOptions())
{
}

AuthManager::AuthManager (ApiClient& client, const juce::PropertiesFile::Options& storageOptions)
    : AuthManager (client, std::make_shared<juce::PropertiesFile> (storageFileFor (storageOptions), storageOptions))
{
}

AuthManager::AuthManager (ApiClient& client, std::shared_ptr<juce::PropertiesFile> sharedStorage)
    : api (client),
      storage (std::move (sharedStorage))
{
    jassert (storage != nullptr);
    loadFromStorage();
}

AuthManager::~AuthManager()
{
    stopTimer();

    if (activeRequest != ApiClient::invalidRequest)
        api.cancel (activeRequest);
}

juce::PropertiesFile::Options AuthManager::defaultStorageOptions()
{
    juce::PropertiesFile::Options options;
    options.applicationName = strings::productName;
    options.filenameSuffix = "settings";
    options.folderName = strings::productName;
    options.osxLibrarySubFolder = "Application Support";
    options.storageFormat = juce::PropertiesFile::storeAsXML;
    return options;
}

juce::File AuthManager::storageFileFor (const juce::PropertiesFile::Options& options)
{
   #if JUCE_LINUX || JUCE_BSD
    const auto folder = options.folderName.isNotEmpty() ? options.folderName : options.applicationName;

    return juce::File::getSpecialLocation (juce::File::userApplicationDataDirectory)
               .getChildFile (folder)
               .getChildFile (options.applicationName + "." + options.filenameSuffix);
   #else
    return options.getDefaultFile();
   #endif
}

juce::File AuthManager::defaultDataDirectory()
{
    return storageFileFor (defaultStorageOptions()).getParentDirectory();
}

//==============================================================================
void AuthManager::login (const juce::String& email, const juce::String& password,
                         std::function<void (std::optional<ApiError>)> onDone)
{
    if (activeRequest != ApiClient::invalidRequest)
    {
        api.cancel (activeRequest);
        activeRequest = ApiClient::invalidRequest;
    }

    setState (State::LoggingIn);

    activeRequest = api.login (email, password, [this, onDone] (ApiClient::Response<AuthTokens> response)
    {
        activeRequest = ApiClient::invalidRequest;

        if (! response.ok())
        {
            const auto error = fallbackError (response.error, "Could not sign in");
            setState (State::LoggedOut);
            listeners.call ([this, &error] (Listener& l) { l.authError (*this, error); });

            if (onDone != nullptr)
                onDone (error);

            return;
        }

        applyTokens (*response.value);
        saveToStorage();
        setState (State::LoggedIn);
        listeners.call ([this] (Listener& l) { l.authStateChanged (*this); });
        refreshBalance();

        if (onDone != nullptr)
            onDone (std::nullopt);
    });
}

void AuthManager::logout()
{
    if (activeRequest != ApiClient::invalidRequest)
    {
        api.cancel (activeRequest);
        activeRequest = ApiClient::invalidRequest;
    }

    stopBalancePolling();

    accessToken.clear();
    refreshToken.clear();
    tokenExpiry = juce::Time();
    user.reset();
    balance.reset();
    referral.reset();
    gifts.clear();

    storage->removeValue (keyAccessToken);
    storage->removeValue (keyRefreshToken);
    storage->removeValue (keyExpiresAtMs);
    storage->removeValue (keyUserId);
    storage->removeValue (keyUserEmail);
    storage->removeValue (keyUserPlan);
    storage->saveIfNeeded();

    api.clearCredentials();

    // Machine access (contract §11) survives a user sign-out.
    if (const auto key = getApiKey(); key.isNotEmpty())
        api.setApiKey (key);

    auto waiting = std::move (pendingRefreshCallbacks);
    pendingRefreshCallbacks.clear();

    setState (State::LoggedOut);

    for (auto& callback : waiting)
        if (callback != nullptr)
            callback (false);
}

std::optional<UserInfo> AuthManager::getUser() const
{
    return user;
}

std::optional<CreditBalance> AuthManager::getBalance() const
{
    return balance;
}

int AuthManager::getAvailableCredits() const
{
    return balance.has_value() ? balance->available : 0;
}

std::optional<ReferralInfo> AuthManager::getReferral() const
{
    return referral;
}

juce::String AuthManager::getAccessToken() const
{
    return accessToken;
}

juce::Time AuthManager::getTokenExpiry() const
{
    return tokenExpiry;
}

bool AuthManager::isTokenExpired (int marginSeconds) const
{
    if (accessToken.isEmpty())
        return true;

    return tokenExpiry <= juce::Time::getCurrentTime() + juce::RelativeTime::seconds (marginSeconds);
}

void AuthManager::refreshIfNeeded (std::function<void (bool)> onDone)
{
    if (accessToken.isNotEmpty() && ! isTokenExpired())
    {
        if (onDone != nullptr)
            onDone (true);

        return;
    }

    if (refreshToken.isEmpty())
    {
        if (onDone != nullptr)
            onDone (false);

        return;
    }

    if (onDone != nullptr)
        pendingRefreshCallbacks.push_back (std::move (onDone));

    if (state == State::Refreshing)
        return;   // one refresh is in flight; this caller rides along with it

    if (activeRequest != ApiClient::invalidRequest)
    {
        api.cancel (activeRequest);
        activeRequest = ApiClient::invalidRequest;
    }

    setState (State::Refreshing);

    activeRequest = api.refresh (refreshToken, [this] (ApiClient::Response<AuthTokens> response)
    {
        activeRequest = ApiClient::invalidRequest;
        const bool ok = response.ok();

        if (ok)
        {
            applyTokens (*response.value);
            saveToStorage();
            setState (State::LoggedIn);
            listeners.call ([this] (Listener& l) { l.authStateChanged (*this); });
        }
        else
        {
            const auto error = fallbackError (response.error, "Could not refresh the session");

            if (error.isUnauthorized() || error.code == "token_expired")
                logout();                     // the refresh token is dead: a new sign-in is required
            else if (state == State::Refreshing)
                setState (State::LoggedIn);   // transient failure: keep the session and retry later

            listeners.call ([this, &error] (Listener& l) { l.authError (*this, error); });
        }

        auto waiting = std::move (pendingRefreshCallbacks);
        pendingRefreshCallbacks.clear();

        for (auto& callback : waiting)
            if (callback != nullptr)
                callback (ok);
    });
}

void AuthManager::refreshBalance (std::function<void (std::optional<ApiError>)> onDone)
{
    if (! api.hasCredentials())
    {
        if (onDone != nullptr)
            onDone (ApiError::transport ("Not signed in"));

        return;
    }

    if (activeRequest != ApiClient::invalidRequest)
    {
        api.cancel (activeRequest);
        activeRequest = ApiClient::invalidRequest;
    }

    activeRequest = api.getMe ([this, onDone] (ApiClient::Response<MeResponse> response)
    {
        activeRequest = ApiClient::invalidRequest;

        if (! response.ok())
        {
            const auto error = fallbackError (response.error, "Could not read your account");
            listeners.call ([this, &error] (Listener& l) { l.authError (*this, error); });

            if (onDone != nullptr)
                onDone (error);

            return;
        }

        user = response.value->user;
        referral = response.value->referral;
        gifts = response.value->gifts;
        saveToStorage();
        updateBalance (response.value->balance);
        listeners.call ([this] (Listener& l) { l.authStateChanged (*this); });

        if (onDone != nullptr)
            onDone (std::nullopt);
    });
}

void AuthManager::updateBalance (const CreditBalance& newBalance)
{
    balance = newBalance;
    listeners.call ([this, &newBalance] (Listener& l) { l.balanceChanged (*this, newBalance); });
}

void AuthManager::startBalancePolling (int intervalMs)
{
    balancePollIntervalMs = juce::jmax (minPollIntervalMs, intervalMs);
    scheduleNextTick();

    if (api.hasCredentials() && state != State::Refreshing)
        refreshBalance();
}

void AuthManager::stopBalancePolling()
{
    balancePollIntervalMs = 0;
    scheduleNextTick();
}

void AuthManager::setApiKey (const juce::String& apiKey)
{
    if (apiKey.isEmpty())
        storage->removeValue (keyApiKey);
    else
        storage->setValue (keyApiKey, apiKey);

    storage->saveIfNeeded();
    api.setApiKey (apiKey);
    listeners.call ([this] (Listener& l) { l.authStateChanged (*this); });
}

juce::String AuthManager::getApiKey() const
{
    return storage->getValue (keyApiKey);
}

void AuthManager::addListener (Listener* listener)
{
    listeners.add (listener);
}

void AuthManager::removeListener (Listener* listener)
{
    listeners.remove (listener);
}

//==============================================================================
void AuthManager::timerCallback()
{
    if (isLoggedIn() && isTokenExpired (tokenRefreshMarginSeconds))
    {
        refreshIfNeeded ([this] (bool ok)
        {
            if (ok && balancePollIntervalMs > 0)
                refreshBalance();
        });

        return;
    }

    if (balancePollIntervalMs > 0 && state != State::Refreshing)
        refreshBalance();
}

void AuthManager::loadFromStorage()
{
    accessToken = storage->getValue (keyAccessToken);
    refreshToken = storage->getValue (keyRefreshToken);
    tokenExpiry = juce::Time (storage->getValue (keyExpiresAtMs, "0").getLargeIntValue());

    UserInfo stored;
    stored.id = storage->getValue (keyUserId);
    stored.email = storage->getValue (keyUserEmail);
    stored.plan = storage->getValue (keyUserPlan);

    if (stored.id.isNotEmpty())
        user = stored;

    if (const auto key = storage->getValue (keyApiKey); key.isNotEmpty())
        api.setApiKey (key);

    if (accessToken.isNotEmpty())
    {
        api.setAccessToken (accessToken);
        state = State::LoggedIn;
    }

    scheduleNextTick();
}

void AuthManager::saveToStorage()
{
    storage->setValue (keyAccessToken, accessToken);
    storage->setValue (keyRefreshToken, refreshToken);
    storage->setValue (keyExpiresAtMs, juce::String (tokenExpiry.toMilliseconds()));

    if (user.has_value())
    {
        storage->setValue (keyUserId, user->id);
        storage->setValue (keyUserEmail, user->email);
        storage->setValue (keyUserPlan, user->plan);
    }

    storage->saveIfNeeded();
}

void AuthManager::applyTokens (const AuthTokens& tokens)
{
    accessToken = tokens.accessToken;
    refreshToken = tokens.refreshToken;
    tokenExpiry = juce::Time::getCurrentTime() + juce::RelativeTime::seconds (juce::jmax (0, tokens.expiresIn));

    if (tokens.user.id.isNotEmpty())
        user = tokens.user;

    api.setAccessToken (accessToken);
}

void AuthManager::setState (State newState)
{
    if (state == newState)
        return;

    state = newState;
    scheduleNextTick();
    listeners.call ([this] (Listener& l) { l.authStateChanged (*this); });
}

void AuthManager::scheduleNextTick()
{
    if (balancePollIntervalMs > 0)
    {
        if (getTimerInterval() != balancePollIntervalMs)
            startTimer (balancePollIntervalMs);

        return;
    }

    if (isLoggedIn())
    {
        if (getTimerInterval() != tokenCheckIntervalMs)
            startTimer (tokenCheckIntervalMs);

        return;
    }

    stopTimer();
}

} // namespace tonamorph::cloud
