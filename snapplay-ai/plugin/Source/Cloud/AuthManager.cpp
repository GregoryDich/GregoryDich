#include "Cloud/AuthManager.h"

namespace snapplay::cloud
{

AuthManager::AuthManager (ApiClient& client)
    : AuthManager (client, defaultStorageOptions())
{
}

AuthManager::AuthManager (ApiClient& client, const juce::PropertiesFile::Options& storageOptions)
    : api (client),
      storage (std::make_unique<juce::PropertiesFile> (storageOptions))
{
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
    options.applicationName = "SnapPlayAI";
    options.filenameSuffix = "settings";
    options.folderName = "SnapPlay";
    options.osxLibrarySubFolder = "Application Support";
    options.storageFormat = juce::PropertiesFile::storeAsXML;
    return options;
}

//==============================================================================
void AuthManager::login (const juce::String& email, const juce::String& password,
                         std::function<void (std::optional<ApiError>)> onDone)
{
    juce::ignoreUnused (email, password, onDone);
}

void AuthManager::logout()
{
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
    juce::ignoreUnused (marginSeconds);
    return accessToken.isEmpty();
}

void AuthManager::refreshIfNeeded (std::function<void (bool)> onDone)
{
    juce::ignoreUnused (onDone);
}

void AuthManager::refreshBalance (std::function<void (std::optional<ApiError>)> onDone)
{
    juce::ignoreUnused (onDone);
}

void AuthManager::updateBalance (const CreditBalance& newBalance)
{
    juce::ignoreUnused (newBalance);
}

void AuthManager::startBalancePolling (int intervalMs)
{
    juce::ignoreUnused (intervalMs);
}

void AuthManager::stopBalancePolling()
{
}

void AuthManager::setApiKey (const juce::String& apiKey)
{
    juce::ignoreUnused (apiKey);
}

juce::String AuthManager::getApiKey() const
{
    return {};
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
}

void AuthManager::loadFromStorage()
{
}

void AuthManager::saveToStorage()
{
}

void AuthManager::applyTokens (const AuthTokens& tokens)
{
    juce::ignoreUnused (tokens);
}

void AuthManager::setState (State newState)
{
    state = newState;
}

void AuthManager::scheduleNextTick()
{
}

} // namespace snapplay::cloud
