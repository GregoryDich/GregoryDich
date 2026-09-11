#pragma once

/**
 * Dark look-and-feel for the Tonamorph editor: one palette shared by every component,
 * arc-style rotary knobs and flat rounded buttons.
 */

#include <JuceHeader.h>

namespace tonamorph::ui
{

namespace colours
{
    inline const juce::Colour background { 0xff15171c };
    inline const juce::Colour panel      { 0xff1e2129 };
    inline const juce::Colour panelLight { 0xff272b35 };
    inline const juce::Colour outline    { 0xff2f3543 };
    inline const juce::Colour accent     { 0xff3fc1b0 };
    inline const juce::Colour accentDim  { 0xff2a9d8f };
    inline const juce::Colour text       { 0xffe6e8ee };
    inline const juce::Colour textDim    { 0xff8a90a0 };
    inline const juce::Colour danger     { 0xffe5646e };
}

class TonamorphLookAndFeel final : public juce::LookAndFeel_V4
{
public:
    TonamorphLookAndFeel();

    /** The editor's UI font at `height` pixels. */
    static juce::Font font (float height, bool bold = false);

    void drawRotarySlider (juce::Graphics&, int x, int y, int width, int height, float sliderPosProportional,
                           float rotaryStartAngle, float rotaryEndAngle, juce::Slider&) override;
    void drawButtonBackground (juce::Graphics&, juce::Button&, const juce::Colour& backgroundColour,
                               bool shouldDrawButtonAsHighlighted, bool shouldDrawButtonAsDown) override;
    juce::Font getTextButtonFont (juce::TextButton&, int buttonHeight) override;
    juce::Font getComboBoxFont (juce::ComboBox&) override;

private:
    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR (TonamorphLookAndFeel)
};

} // namespace tonamorph::ui
