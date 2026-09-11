#pragma once

/**
 * A one-line message floating over the keyboard: celebrations and onboarding hints.
 * `show (text, durationMs)` fades the toast out after the duration; 0 keeps it until
 * hide(). Visual only; message thread.
 */

#include <JuceHeader.h>

namespace tonamorph::ui
{

class MessageToast final : public juce::Component,
                           private juce::Timer
{
public:
    MessageToast();
    ~MessageToast() override;

    void show (const juce::String& text, int durationMs);
    void hide();
    bool isShowing (const juce::String& text) const;

    void paint (juce::Graphics& g) override;
    void resized() override;

private:
    void timerCallback() override;

    static constexpr int fadeMs = 400;
    static constexpr int frameIntervalMs = 33;

    juce::Label label;
    double hideAtMs = 0.0;   ///< 0 = sticky
    float alpha = 1.0f;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR (MessageToast)
};

} // namespace tonamorph::ui
