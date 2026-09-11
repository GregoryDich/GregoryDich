#pragma once

/**
 * The strip above the header fed by `GET /v1/version`: "<product> <latest> is available."
 * with Download and Dismiss, or a persistent "Update required" bar (no Dismiss) when the
 * running version is below `min_supported`. Hidden otherwise.
 */

#include <JuceHeader.h>

#include <functional>

namespace tonamorph::ui
{

class VersionBanner final : public juce::Component
{
public:
    static constexpr int preferredHeight = 34;

    VersionBanner();

    void showUpdateAvailable (const juce::String& latestVersion, const juce::String& downloadUrl);
    void showUpdateRequired (const juce::String& downloadUrl);
    void hide();
    bool isRequired() const noexcept { return required; }

    /** Fired by Dismiss (only offered for the optional update). */
    std::function<void()> onDismiss;

    void paint (juce::Graphics& g) override;
    void resized() override;

private:
    juce::Label label;
    juce::TextButton downloadButton;
    juce::TextButton dismissButton;
    juce::String url;
    bool required = false;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR (VersionBanner)
};

} // namespace tonamorph::ui
