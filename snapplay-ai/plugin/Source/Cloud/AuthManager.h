#pragma once

/**
 * Session state for the signed-in user (contract §1, §3).
 *
 * Persists the access/refresh tokens (never the password) and the optional API key in a
 * juce::PropertiesFile, tracks expiry, refreshes the access token automatically before it
 * expires, keeps the credit balance current and notifies listeners. All public methods
 * must be called on the message thread; callbacks arrive on the message thread.
 */

#include <JuceHeader.h>

#include "Cloud/ApiClient.h"
#include "Cloud/Models.h"

#include <functional>
#include <memory>
#include <optional>

namespace snapplay::cloud
{

class AuthManager : private juce::Timer
{
public:
    enum class State { LoggedOut, LoggingIn, LoggedIn, Refreshing };

    /** Notifications are delivered on the message thread. */
    class Listener
    {
    public:
        virtual ~Listener() = default;
        /** Login, logout, refresh success/failure or user info change. */
        virtual void authStateChanged (AuthManager&) {}
        /** A new balance arrived (from /v1/me or a job response). */
        virtual void balanceChanged (AuthManager&, const CreditBalance& balance) { juce::ignoreUnused (balance); }
        /** A login/refresh/balance request failed. */
        virtual void authError (AuthManager&, const ApiError& error) { juce::ignoreUnused (error); }
    };

    /** Uses defaultStorageOptions() and immediately loads any persisted session. */
    explicit AuthManager (ApiClient& client);
    AuthManager (ApiClient& client, const juce::PropertiesFile::Options& storageOptions);
    ~AuthManager() override;

    /** applicationName "SnapPlayAI", filenameSuffix "settings", folderName "SnapPlay",
        osxLibrarySubFolder "Application Support". */
    static juce::PropertiesFile::Options defaultStorageOptions();

    //==============================================================================
    /** POST /v1/auth/token; on success persists the tokens, installs them on the
        ApiClient and fetches /v1/me. `onDone` receives nullopt on success. */
    void login (const juce::String& email, const juce::String& password,
                std::function<void (std::optional<ApiError>)> onDone = {});
    /** Clears tokens from memory, storage and the ApiClient (API key is kept). */
    void logout();

    State getState() const noexcept { return state; }
    bool isLoggedIn() const noexcept { return state == State::LoggedIn || state == State::Refreshing; }
    std::optional<UserInfo> getUser() const;
    std::optional<CreditBalance> getBalance() const;
    /** Convenience: `balance.available`, or 0 when unknown. */
    int getAvailableCredits() const;

    juce::String getAccessToken() const;
    juce::Time getTokenExpiry() const;
    /** True when the token expires within `marginSeconds` (or is missing). */
    bool isTokenExpired (int marginSeconds = 60) const;

    /** Refreshes the access token if it is expired or about to expire; otherwise calls
        `onDone (true)` immediately. Concurrent calls coalesce onto one request. */
    void refreshIfNeeded (std::function<void (bool ok)> onDone = {});
    /** GET /v1/me; updates user info and balance, then notifies. */
    void refreshBalance (std::function<void (std::optional<ApiError>)> onDone = {});
    /** Installs a balance received from another response (job submit/result). */
    void updateBalance (const CreditBalance& balance);

    /** Polls GET /v1/me every `intervalMs` while the paywall is open (contract §3: 5 s). */
    void startBalancePolling (int intervalMs = 5000);
    void stopBalancePolling();
    bool isPollingBalance() const noexcept { return balancePollIntervalMs > 0; }

    /** Machine-access key (contract §11); persisted and installed on the ApiClient.
        Empty removes it. */
    void setApiKey (const juce::String& apiKey);
    juce::String getApiKey() const;

    void addListener (Listener* listener);
    void removeListener (Listener* listener);

private:
    void timerCallback() override;
    void loadFromStorage();
    void saveToStorage();
    void applyTokens (const AuthTokens& tokens);
    void setState (State newState);
    void scheduleNextTick();

    ApiClient& api;
    std::unique_ptr<juce::PropertiesFile> storage;
    juce::ListenerList<Listener> listeners;

    State state = State::LoggedOut;
    juce::String accessToken;
    juce::String refreshToken;
    juce::Time tokenExpiry;
    std::optional<UserInfo> user;
    std::optional<CreditBalance> balance;

    ApiClient::RequestId activeRequest = ApiClient::invalidRequest;
    std::vector<std::function<void (bool)>> pendingRefreshCallbacks;
    int balancePollIntervalMs = 0;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR (AuthManager)
};

} // namespace snapplay::cloud
