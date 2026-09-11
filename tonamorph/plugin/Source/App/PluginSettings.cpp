#include "App/PluginSettings.h"

#include "Cloud/AuthManager.h"

namespace tonamorph
{

namespace
{
    constexpr const char* keyCrashReports     = "crashReports.optIn";
    constexpr const char* keyRatedJobs        = "feedback.ratedJobs";
    constexpr const char* keyVersionCheckedMs = "version.lastCheckMs";
    constexpr const char* keyVersionInfo      = "version.lastResponse";
    constexpr const char* keyVersionDismissed = "version.dismissed";
} // namespace

PluginSettings::PluginSettings()
    : PluginSettings (cloud::AuthManager::defaultStorageOptions())
{
}

PluginSettings::PluginSettings (const juce::PropertiesFile::Options& options)
    : file (std::make_shared<juce::PropertiesFile> (options))
{
}

//==============================================================================
bool PluginSettings::isCrashReportingEnabled() const
{
    return file->getBoolValue (keyCrashReports, false);
}

void PluginSettings::setCrashReportingEnabled (bool enabled)
{
    file->setValue (keyCrashReports, enabled);
    file->saveIfNeeded();
}

//==============================================================================
bool PluginSettings::hasSeen (const juce::String& flag) const
{
    return file->getBoolValue (flag, false);
}

void PluginSettings::markSeen (const juce::String& flag)
{
    if (hasSeen (flag))
        return;

    file->setValue (flag, true);
    file->saveIfNeeded();
}

//==============================================================================
bool PluginSettings::wasJobRated (const juce::String& jobId) const
{
    return juce::StringArray::fromTokens (file->getValue (keyRatedJobs), ",", {}).contains (jobId);
}

void PluginSettings::markJobRated (const juce::String& jobId)
{
    auto rated = juce::StringArray::fromTokens (file->getValue (keyRatedJobs), ",", {});
    rated.removeEmptyStrings();
    rated.removeString (jobId);
    rated.add (jobId);

    while (rated.size() > maxRememberedRatings)
        rated.remove (0);

    file->setValue (keyRatedJobs, rated.joinIntoString (","));
    file->saveIfNeeded();
}

//==============================================================================
juce::Time PluginSettings::getLastVersionCheck() const
{
    return juce::Time (file->getValue (keyVersionCheckedMs, "0").getLargeIntValue());
}

void PluginSettings::setLastVersionCheck (juce::Time time)
{
    file->setValue (keyVersionCheckedMs, juce::String (time.toMilliseconds()));
    file->saveIfNeeded();
}

std::optional<cloud::VersionInfo> PluginSettings::getCachedVersionInfo() const
{
    const auto text = file->getValue (keyVersionInfo);

    if (text.isEmpty())
        return std::nullopt;

    return cloud::VersionInfo::fromJson (juce::JSON::parse (text));
}

void PluginSettings::setCachedVersionInfo (const cloud::VersionInfo& info)
{
    file->setValue (keyVersionInfo, juce::JSON::toString (info.toVar(), true));
    file->saveIfNeeded();
}

juce::String PluginSettings::getDismissedUpdateVersion() const
{
    return file->getValue (keyVersionDismissed);
}

void PluginSettings::setDismissedUpdateVersion (const juce::String& version)
{
    file->setValue (keyVersionDismissed, version);
    file->saveIfNeeded();
}

} // namespace tonamorph
