#include "TestFramework.h"

#include "Core/CrashReportText.h"

#include <string>

using namespace tonamorph::core;

TONAMORPH_TEST(crashReportRoundTripsThroughText)
{
    CrashReport report;
    report.pluginVersion = "0.1.0";
    report.os = "Linux 6.1";
    report.host = "Reaper";
    report.occurredAt = "2026-09-11T12:00:00Z";
    report.backtrace = "0: libTonamorph.so(+0x1234)\n1: host(+0x99)";

    const auto text = formatCrashReport(report);
    TONAMORPH_CHECK(text.find("plugin_version: 0.1.0\n") == 0);
    TONAMORPH_CHECK(text.find("host: Reaper\n") != std::string::npos);

    const auto parsed = parseCrashReport(text);
    TONAMORPH_CHECK(parsed.has_value());
    TONAMORPH_CHECK_EQ(parsed->pluginVersion, report.pluginVersion);
    TONAMORPH_CHECK_EQ(parsed->os, report.os);
    TONAMORPH_CHECK_EQ(parsed->host, report.host);
    TONAMORPH_CHECK_EQ(parsed->occurredAt, report.occurredAt);
    TONAMORPH_CHECK_EQ(parsed->backtrace, report.backtrace + "\n");

    TONAMORPH_CHECK(!parseCrashReport("os: x\n").has_value());
    TONAMORPH_CHECK(!parseCrashReport("").has_value());
}

TONAMORPH_TEST(crashReportJsonCarriesEveryFieldAndOptIn)
{
    CrashReport report;
    report.pluginVersion = "0.1.0";
    report.os = "macOS 14";
    report.host = "Ableton Live";
    report.occurredAt = "2026-09-11T12:00:00Z";
    report.backtrace = "a \"b\"\nc";

    TONAMORPH_CHECK_EQ(buildCrashReportJson(report),
                       std::string(R"({"plugin_version":"0.1.0","os":"macOS 14","host":"Ableton Live",)"
                                   R"("occurred_at":"2026-09-11T12:00:00Z","backtrace":"a \"b\"\nc","opted_in":true})"));
}

TONAMORPH_TEST(crashReportScrubsHomeDirectoryAndUserName)
{
    const std::string trace = "/home/gregory/.vst3/x.so(+0x1)\nC:\\Users\\gregory\\AppData\\x.dll\n/opt/host";
    const auto scrubbed = scrubUserPaths(trace, "/home/gregory/", "gregory");

    TONAMORPH_CHECK(scrubbed.find("/home/gregory") == std::string::npos);
    TONAMORPH_CHECK(scrubbed.find("gregory") == std::string::npos);
    TONAMORPH_CHECK(scrubbed.find("~/.vst3/x.so") != std::string::npos);
    TONAMORPH_CHECK(scrubbed.find("C:\\Users\\<user>\\AppData") != std::string::npos);
    TONAMORPH_CHECK(scrubbed.find("/opt/host") != std::string::npos);

    // Degenerate inputs must not blank the report.
    TONAMORPH_CHECK_EQ(scrubUserPaths("abc", "/", ""), std::string("abc"));
    TONAMORPH_CHECK_EQ(scrubUserPaths("abc", "", "a"), std::string("abc"));
}
