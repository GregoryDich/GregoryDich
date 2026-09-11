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
    constexpr const char* keyFirstMorphAtMs   = "firstMorph.atMs";
    constexpr const char* keyNpsAnswered      = "nps.answered";
    constexpr const char* keyNpsDismissals    = "nps.dismissals";
} // namespace

PluginSettings::PluginSettings()
    : PluginSettings (cloud::AuthManager::defaultStorageOptions())
{
}

PluginSettings::PluginSettings (const juce::PropertiesFile::Options& options)
    : file (std::make_shared<juce::PropertiesFile> (cloud::AuthManager::storageFileFor (options), options))
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
std::optional<juce::Time> PluginSettings::getFirstMorphAt() const
{
    const auto ms = file->getValue (keyFirstMorphAtMs).getLargeIntValue();

    if (ms <= 0)
        return std::nullopt;

    return juce::Time (ms);
}

void PluginSettings::markFirstMorph (juce::Time time)
{
    if (getFirstMorphAt().has_value())
        return;

    file->setValue (keyFirstMorphAtMs, juce::String (time.toMilliseconds()));
    file->saveIfNeeded();
}

bool PluginSettings::wasNpsAnswered() const
{
    return file->getBoolValue (keyNpsAnswered, false);
}

void PluginSettings::setNpsAnswered()
{
    file->setValue (keyNpsAnswered, true);
    file->saveIfNeeded();
}

int PluginSettings::getNpsDismissals() const
{
    return file->getIntValue (keyNpsDismissals, 0);
}

void PluginSettings::incrementNpsDismissals()
{
    file->setValue (keyNpsDismissals, getNpsDismissals() + 1);
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
