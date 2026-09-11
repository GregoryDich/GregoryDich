#pragma once

/**
 * The on-screen keyboard with two visual-only overlays: a two-second glow on the keys of
 * the detected scale (the first-morph celebration) and a highlighted note (the "Play C3"
 * hint). Nothing here touches audio; drawing happens on the message thread.
 */

#include <JuceHeader.h>

#include <cstdint>
#include <functional>
#include <vector>

namespace tonamorph::ui
{

class ScaleKeyboard final : public juce::MidiKeyboardComponent
{
public:
    ScaleKeyboard (juce::MidiKeyboardState& stateToUse, Orientation orientationToUse);
    ~ScaleKeyboard() override;

    /** Tints every key whose pitch class is listed, fading out after `durationMs`. */
    void glowPitchClasses (const std::vector<int>& pitchClasses, int durationMs);
    /** Marks one note until cleared; -1 clears. */
    void setHighlightedNote (int midiNote);
    void clearOverlays();

protected:
    void drawWhiteNote (int midiNoteNumber, juce::Graphics& g, juce::Rectangle<float> area, bool isDown,
                        bool isOver, juce::Colour lineColour, juce::Colour textColour) override;
    void drawBlackNote (int midiNoteNumber, juce::Graphics& g, juce::Rectangle<float> area, bool isDown,
                        bool isOver, juce::Colour noteFillColour) override;

private:
    /** Alpha of the glow right now: fades in over the first 150 ms, out over the last 500 ms. */
    float glowAlphaNow() const;
    void drawOverlays (int midiNoteNumber, juce::Graphics& g, juce::Rectangle<float> area);

    /** A separate timer: the base class owns its own private juce::Timer. */
    struct Ticker final : juce::Timer
    {
        std::function<void()> onTick;
        void timerCallback() override { if (onTick != nullptr) onTick(); }
    };

    Ticker ticker;
    std::uint16_t glowMask = 0;
    double glowStartMs = 0.0;
    int glowDurationMs = 0;
    int highlightedNote = -1;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR (ScaleKeyboard)
};

} // namespace tonamorph::ui
