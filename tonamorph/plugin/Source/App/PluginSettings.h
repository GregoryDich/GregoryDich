#pragma once

/**
 * The plugin's own settings file (`<user app data>/<product>/<product>.settings`), shared
 * with AuthManager through one juce::PropertiesFile so no writer clobbers another's keys.
 * Holds preferences and "seen" flags that belong to the person, not to a DAW project:
 * crash-report opt-in, celebration and hint flags, rated jobs and the version-check cache.
 * Message thread only.
 */

#include <JuceHeader.h>

#include "Cloud/Models.h"

#include <memory>
#include <optional>

namespace tonamorph
{

class PluginSettings
{
public:
    /** Uses cloud::AuthManager::defaultStorageOptions(). */
    PluginSettings();
    explicit PluginSettings (const juce::PropertiesFile::Options& options);

    std::shared_ptr<juce::PropertiesFile> getFile() const noexcept { return file; }

    //==============================================================================
    /** "Send anonymous crash reports" — default off. */
    bool isCrashReportingEnabled() const;
    void setCrashReportingEnabled (bool enabled);

    //==============================================================================
    static constexpr const char* flagFirstMorph     = "seen.celebration.firstMorph";
    static constexpr const char* flagFirstDrag      = "seen.celebration.firstDrag";
    static constexpr const char* flagFirstPurchase  = "seen.celebration.firstPurchase";
    static constexpr const char* flagFirstSoundHint = "seen.hint.firstSound";
    static constexpr const char* flagFirstDragHint  = "seen.hint.firstDrag";

    bool hasSeen (const juce::String& flag) const;
    void markSeen (const juce::String& flag);

    //==============================================================================
    /** One rating per job: remembered so the control stays hidden across sessions. */
    bool wasJobRated (const juce::String& jobId) const;
    void markJobRated (const juce::String& jobId);

    //==============================================================================
    /** `GET /v1/version` is called at most once per 24 h; the last answer is cached so the
        banner survives editor re-opens without another request. */
    juce::Time getLastVersionCheck() const;
    void setLastVersionCheck (juce::Time time);
    std::optional<cloud::VersionInfo> getCachedVersionInfo() const;
    void setCachedVersionInfo (const cloud::VersionInfo& info);
    /** The `latest` the person dismissed; the banner stays hidden for that version only. */
    juce::String getDismissedUpdateVersion() const;
    void setDismissedUpdateVersion (const juce::String& version);

private:
    static constexpr int maxRememberedRatings = 200;

    std::shared_ptr<juce::PropertiesFile> file;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR (PluginSettings)
};

} // namespace tonamorph
