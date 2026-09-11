#pragma once

/**
 * The on-disk crash report and its `POST /v1/telemetry/crash` body. The report is a
 * plain-text key/value block (written from the crash handler, so it must stay trivial)
 * holding the plugin version, OS, host, timestamp and backtrace — never audio, tokens or
 * paths that reveal a user name. Standard-library only so the formatting and scrubbing
 * are unit-tested without JUCE.
 */

#include <optional>
#include <string>
#include <string_view>

#include "Core/FeedbackPayload.h"   // jsonEscape

namespace tonamorph::core
{

struct CrashReport
{
    std::string pluginVersion;
    std::string os;
    std::string host;
    std::string occurredAt;   ///< RFC 3339 UTC
    std::string backtrace;
};

inline constexpr const char* crashReportBacktraceMarker = "backtrace:\n";

/** Replaces the home directory with "~" and the user name with "<user>" wherever they
    appear, so a backtrace never carries the account name. Empty inputs are ignored. */
inline std::string scrubUserPaths (std::string text, std::string_view homeDirectory, std::string_view userName)
{
    auto replaceAll = [&text] (std::string_view from, std::string_view to)
    {
        if (from.empty())
            return;

        for (auto pos = text.find (from); pos != std::string::npos; pos = text.find (from, pos + to.size()))
            text.replace (pos, from.size(), to);
    };

    std::string home (homeDirectory);

    while (home.size() > 1 && (home.back() == '/' || home.back() == '\\'))
        home.pop_back();

    if (home.size() > 1)
        replaceAll (home, "~");

    if (userName.size() > 1)
        replaceAll (userName, "<user>");

    return text;
}

/** Serialises a report as the text block the handler writes. */
inline std::string formatCrashReport (const CrashReport& report)
{
    std::string text;
    text.reserve (256 + report.backtrace.size());
    text += "plugin_version: " + report.pluginVersion + '\n';
    text += "os: " + report.os + '\n';
    text += "host: " + report.host + '\n';
    text += "occurred_at: " + report.occurredAt + '\n';
    text += crashReportBacktraceMarker;
    text += report.backtrace;

    if (! report.backtrace.empty() && report.backtrace.back() != '\n')
        text += '\n';

    return text;
}

/** Reads a block written by formatCrashReport(); nullopt when the header is incomplete. */
inline std::optional<CrashReport> parseCrashReport (std::string_view text)
{
    CrashReport report;
    const auto marker = text.find (crashReportBacktraceMarker);

    if (marker == std::string_view::npos)
        return std::nullopt;

    auto header = text.substr (0, marker);
    report.backtrace = std::string (text.substr (marker + std::string_view (crashReportBacktraceMarker).size()));

    auto readLine = [&header] (std::string_view key, std::string& out)
    {
        const std::string prefix = std::string (key) + ": ";
        const auto start = header.find (prefix);

        if (start == std::string_view::npos || (start != 0 && header[start - 1] != '\n'))
            return false;

        const auto valueStart = start + prefix.size();
        auto end = header.find ('\n', valueStart);

        if (end == std::string_view::npos)
            end = header.size();

        out = std::string (header.substr (valueStart, end - valueStart));
        return true;
    };

    if (! readLine ("plugin_version", report.pluginVersion) || ! readLine ("os", report.os)
        || ! readLine ("host", report.host) || ! readLine ("occurred_at", report.occurredAt))
        return std::nullopt;

    return report;
}

/** `{ plugin_version, os, host, occurred_at, backtrace, opted_in: true }`. */
inline std::string buildCrashReportJson (const CrashReport& report)
{
    std::string json = "{\"plugin_version\":\"" + jsonEscape (report.pluginVersion) + '"';
    json += ",\"os\":\"" + jsonEscape (report.os) + '"';
    json += ",\"host\":\"" + jsonEscape (report.host) + '"';
    json += ",\"occurred_at\":\"" + jsonEscape (report.occurredAt) + '"';
    json += ",\"backtrace\":\"" + jsonEscape (report.backtrace) + '"';
    json += ",\"opted_in\":true}";
    return json;
}

} // namespace tonamorph::core
