#include "App/CrashReporter.h"

#include "Cloud/AuthManager.h"

#include "Core/CrashReportText.h"
#include "Core/Strings.h"

#include <atomic>
#include <cstdio>
#include <string>

namespace tonamorph
{

namespace
{
    // Everything the handler needs is prepared at install time: a crash handler should
    // not discover paths or query the system while the process is already broken.
    std::atomic<bool> installed { false };
    std::atomic<bool> handling { false };
    std::string headerVersion;
    std::string headerOs;
    std::string headerHost;
    std::string directoryPath;
    std::string homePath;
    std::string userName;

    juce::String fileNameFor (juce::Time occurredAt)
    {
        return "crash-" + juce::String (occurredAt.toMilliseconds()) + ".txt";
    }

    bool isReportFile (const juce::File& file)
    {
        return file.getFileName().startsWith ("crash-") && file.hasFileExtension ("txt");
    }
} // namespace

//==============================================================================
void CrashReporter::install (const juce::String& pluginVersion, const juce::String& hostName)
{
    if (installed.exchange (true))
        return;

    headerVersion = pluginVersion.toStdString();
    headerOs = (juce::SystemStats::getOperatingSystemName() + " " + juce::SystemStats::getDeviceDescription()).trim().toStdString();
    headerHost = hostName.toStdString();
    homePath = juce::File::getSpecialLocation (juce::File::userHomeDirectory).getFullPathName().toStdString();
    userName = juce::SystemStats::getLogonName().toStdString();

    const auto directory = reportDirectory();
    directory.createDirectory();
    directoryPath = directory.getFullPathName().toStdString();

    juce::SystemStats::setApplicationCrashHandler (&CrashReporter::handleCrash);
}

bool CrashReporter::isInstalled() noexcept
{
    return installed.load();
}

juce::File CrashReporter::reportDirectory()
{
    return cloud::AuthManager::defaultDataDirectory().getChildFile ("crash");
}

//==============================================================================
juce::File CrashReporter::writeReport (const juce::String& backtrace, juce::Time occurredAt)
{
    if (directoryPath.empty())
        return {};

    core::CrashReport report;
    report.pluginVersion = headerVersion;
    report.os = headerOs;
    report.host = headerHost;
    report.occurredAt = occurredAt.toISO8601 (true).toStdString();
    report.backtrace = core::scrubUserPaths (backtrace.toStdString(), homePath, userName);

    const auto text = core::formatCrashReport (report);
    const auto path = directoryPath + "/" + fileNameFor (occurredAt).toStdString();

    if (std::FILE* out = std::fopen (path.c_str(), "wb"))
    {
        std::fwrite (text.data(), 1, text.size(), out);
        std::fclose (out);
        return juce::File (path);
    }

    return {};
}

void CrashReporter::handleCrash (void*)
{
    if (handling.exchange (true))
        return;

    writeReport (juce::SystemStats::getStackBacktrace(), juce::Time::getCurrentTime());
}

//==============================================================================
void CrashReporter::flushPendingReports (cloud::ApiClient& api, bool optedIn)
{
    const auto directory = reportDirectory();

    if (! directory.isDirectory())
        return;

    const auto cutoff = juce::Time::getCurrentTime() - juce::RelativeTime::days (retentionDays);

    for (const auto& entry : juce::RangedDirectoryIterator (directory, false, "*.txt", juce::File::findFiles))
    {
        const auto file = entry.getFile();

        if (! isReportFile (file))
            continue;

        if (! optedIn)
        {
            if (entry.getModificationTime() < cutoff)
                file.deleteFile();

            continue;
        }

        const auto parsed = core::parseCrashReport (file.loadFileAsString().toStdString());

        if (! parsed.has_value())
        {
            file.deleteFile();   // not something this plugin wrote; never upload it
            continue;
        }

        api.postCrashReport (juce::String (core::buildCrashReportJson (*parsed)),
                             [file] (cloud::ApiClient::Response<bool> response)
                             {
                                 // Accepted, or refused for good (a 4xx will not change on retry): drop it.
                                 // A transport failure or 5xx keeps the file for the next launch.
                                 if (response.ok() || (response.statusCode >= 400 && response.statusCode < 500))
                                     file.deleteFile();
                             });
    }
}

} // namespace tonamorph
