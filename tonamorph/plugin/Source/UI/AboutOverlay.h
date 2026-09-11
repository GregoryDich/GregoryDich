#pragma once

/**
 * The About screen: product name and version, the website link, the crash-report opt-in
 * (the same setting as the Settings menu) and the third-party notices rendered from
 * THIRD_PARTY_LICENSES.md at configure time (action 8 of that file) — scrollable,
 * selectable, with a Copy button. Message thread.
 */

#include <JuceHeader.h>

#include "UI/PanelOverlay.h"

#include <functional>

namespace tonamorph::ui
{

class AboutOverlay final : public PanelOverlay,
                           private juce::Timer
{
public:
    AboutOverlay();
    ~AboutOverlay() override;

    /** The notices text embedded at build time (DemoData::third_party_notices_txt). */
    void setNoticesText (const juce::String& text);
    /** Reflects the persisted setting; the toggle fires onCrashReportingChanged. */
    void setCrashReportingEnabled (bool enabled);
    std::function<void (bool enabled)> onCrashReportingChanged;

    void resized() override;

private:
    void timerCallback() override;

    static constexpr int copiedVisibleMs = 1800;

    juce::Label titleLabel;
    juce::Label versionLabel;
    juce::HyperlinkButton websiteLink;
    juce::ToggleButton crashReportsToggle;
    juce::Label noticesLabel;
    juce::TextEditor noticesEditor;
    juce::TextButton copyButton;
    juce::Label copiedLabel;
    juce::TextButton closeButton;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR (AboutOverlay)
};

} // namespace tonamorph::ui
