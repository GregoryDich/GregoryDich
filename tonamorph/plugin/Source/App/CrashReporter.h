#pragma once

/**
 * Opt-in crash reporter (GTM Appendix B §7). While "Send anonymous crash reports" is on,
 * a process-wide juce::SystemStats crash handler writes a plain-text report — plugin
 * version, OS, host, timestamp and juce::SystemStats::getStackBacktrace() with the home
 * directory and user name scrubbed; never audio, tokens or project paths — into the
 * plugin's data directory. The next time an editor opens, pending reports are posted to
 * `POST /v1/telemetry/crash` and deleted; with the option off they are deleted after 7
 * days instead. Nothing here runs on the audio thread. The handler is installed only when
 * the person opted in, so a host's own crash handling stays untouched otherwise.
 */

#include <JuceHeader.h>

#include "Cloud/ApiClient.h"

namespace tonamorph
{

class CrashReporter
{
public:
    /** Installs the process-wide handler once (later calls are no-ops). Message thread. */
    static void install (const juce::String& pluginVersion, const juce::String& hostName);
    static bool isInstalled() noexcept;

    /** `<user app data>/<product>/crash`. */
    static juce::File reportDirectory();
    static constexpr int retentionDays = 7;

    /** Message thread. With `optedIn`, posts every report and deletes it once the server
        answered (2xx, or a 4xx that would never accept it); otherwise deletes reports older
        than retentionDays. */
    static void flushPendingReports (cloud::ApiClient& api, bool optedIn);

    /** Writes a report file for the given backtrace (what the handler does; exposed so the
        path and format can be exercised without crashing). Returns the file or a
        non-existent File on failure. */
    static juce::File writeReport (const juce::String& backtrace, juce::Time occurredAt);

private:
    static void handleCrash (void*);
    CrashReporter() = delete;
};

} // namespace tonamorph
