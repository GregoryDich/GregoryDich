#include "UI/SnapPlayLookAndFeel.h"

namespace snapplay::ui
{

SnapPlayLookAndFeel::SnapPlayLookAndFeel()
    : juce::LookAndFeel_V4 (ColourScheme { colours::background, colours::panel, colours::panel, colours::outline,
                                           colours::text, colours::accent, juce::Colours::white, colours::accentDim,
                                           colours::text })
{
    setColour (juce::ResizableWindow::backgroundColourId, colours::background);
    setColour (juce::Label::textColourId, colours::text);

    setColour (juce::Slider::rotarySliderFillColourId, colours::accent);
    setColour (juce::Slider::rotarySliderOutlineColourId, colours::outline);
    setColour (juce::Slider::thumbColourId, colours::text);
    setColour (juce::Slider::textBoxTextColourId, colours::text);
    setColour (juce::Slider::textBoxBackgroundColourId, juce::Colours::transparentBlack);
    setColour (juce::Slider::textBoxOutlineColourId, juce::Colours::transparentBlack);
    setColour (juce::Slider::textBoxHighlightColourId, colours::accent.withAlpha (0.4f));

    setColour (juce::TextButton::buttonColourId, colours::panel);
    setColour (juce::TextButton::buttonOnColourId, colours::accent);
    setColour (juce::TextButton::textColourOffId, colours::text);
    setColour (juce::TextButton::textColourOnId, colours::background);

    setColour (juce::ToggleButton::textColourId, colours::text);
    setColour (juce::ToggleButton::tickColourId, colours::accent);
    setColour (juce::ToggleButton::tickDisabledColourId, colours::textDim);

    setColour (juce::ComboBox::backgroundColourId, colours::panel);
    setColour (juce::ComboBox::textColourId, colours::text);
    setColour (juce::ComboBox::outlineColourId, colours::outline);
    setColour (juce::ComboBox::arrowColourId, colours::textDim);
    setColour (juce::ComboBox::focusedOutlineColourId, colours::accent);

    setColour (juce::PopupMenu::backgroundColourId, colours::panel);
    setColour (juce::PopupMenu::textColourId, colours::text);
    setColour (juce::PopupMenu::highlightedBackgroundColourId, colours::accentDim);
    setColour (juce::PopupMenu::highlightedTextColourId, juce::Colours::white);

    setColour (juce::TextEditor::backgroundColourId, colours::panel);
    setColour (juce::TextEditor::textColourId, colours::text);
    setColour (juce::TextEditor::outlineColourId, colours::outline);
    setColour (juce::TextEditor::focusedOutlineColourId, colours::accent);
    setColour (juce::TextEditor::highlightColourId, colours::accent.withAlpha (0.4f));
    setColour (juce::CaretComponent::caretColourId, colours::accent);

    setColour (juce::ProgressBar::backgroundColourId, colours::panel);
    setColour (juce::ProgressBar::foregroundColourId, colours::accent);

    setColour (juce::HyperlinkButton::textColourId, colours::accent);

    setColour (juce::MidiKeyboardComponent::whiteNoteColourId, colours::text);
    setColour (juce::MidiKeyboardComponent::blackNoteColourId, juce::Colour (0xff23262e));
    setColour (juce::MidiKeyboardComponent::keySeparatorLineColourId, colours::outline);
    setColour (juce::MidiKeyboardComponent::mouseOverKeyOverlayColourId, colours::accent.withAlpha (0.4f));
    setColour (juce::MidiKeyboardComponent::keyDownOverlayColourId, colours::accent.withAlpha (0.75f));
    setColour (juce::MidiKeyboardComponent::textLabelColourId, colours::background);
    setColour (juce::MidiKeyboardComponent::shadowColourId, juce::Colours::black.withAlpha (0.3f));
}

juce::Font SnapPlayLookAndFeel::font (float height, bool bold)
{
    const auto options = juce::FontOptions (height);
    return juce::Font (bold ? options.withStyle ("Bold") : options);
}

void SnapPlayLookAndFeel::drawRotarySlider (juce::Graphics& g, int x, int y, int width, int height,
                                            float sliderPosProportional, float rotaryStartAngle,
                                            float rotaryEndAngle, juce::Slider& slider)
{
    const auto bounds = juce::Rectangle<int> (x, y, width, height).toFloat().reduced (6.0f);
    const auto radius = juce::jmin (bounds.getWidth(), bounds.getHeight()) * 0.5f;
    const auto centre = bounds.getCentre();
    const auto angle = rotaryStartAngle + sliderPosProportional * (rotaryEndAngle - rotaryStartAngle);
    const auto lineWidth = juce::jmax (2.0f, radius * 0.12f);
    const auto arcRadius = radius - lineWidth * 0.5f;
    const juce::PathStrokeType stroke (lineWidth, juce::PathStrokeType::curved, juce::PathStrokeType::rounded);

    juce::Path track;
    track.addCentredArc (centre.x, centre.y, arcRadius, arcRadius, 0.0f, rotaryStartAngle, rotaryEndAngle, true);
    g.setColour (slider.findColour (juce::Slider::rotarySliderOutlineColourId));
    g.strokePath (track, stroke);

    if (slider.isEnabled())
    {
        juce::Path value;
        value.addCentredArc (centre.x, centre.y, arcRadius, arcRadius, 0.0f, rotaryStartAngle, angle, true);
        g.setColour (slider.findColour (juce::Slider::rotarySliderFillColourId));
        g.strokePath (value, stroke);
    }

    const auto bodyRadius = arcRadius - lineWidth * 1.5f;
    g.setColour (colours::panelLight);
    g.fillEllipse (juce::Rectangle<float> (bodyRadius * 2.0f, bodyRadius * 2.0f).withCentre (centre));

    juce::Path pointer;
    pointer.addRoundedRectangle (-lineWidth * 0.5f, -bodyRadius + 3.0f, lineWidth, bodyRadius * 0.45f, lineWidth * 0.5f);
    pointer.applyTransform (juce::AffineTransform::rotation (angle).translated (centre));
    g.setColour (slider.findColour (juce::Slider::thumbColourId).withMultipliedAlpha (slider.isEnabled() ? 1.0f : 0.4f));
    g.fillPath (pointer);
}

void SnapPlayLookAndFeel::drawButtonBackground (juce::Graphics& g, juce::Button& button,
                                                const juce::Colour& backgroundColour,
                                                bool shouldDrawButtonAsHighlighted, bool shouldDrawButtonAsDown)
{
    const auto bounds = button.getLocalBounds().toFloat().reduced (0.5f);
    constexpr float cornerSize = 6.0f;

    auto fill = backgroundColour;

    if (shouldDrawButtonAsDown)
        fill = fill.brighter (0.15f);
    else if (shouldDrawButtonAsHighlighted)
        fill = fill.brighter (0.08f);

    if (! button.isEnabled())
        fill = fill.withMultipliedAlpha (0.5f);

    g.setColour (fill);
    g.fillRoundedRectangle (bounds, cornerSize);
    g.setColour (button.getToggleState() ? colours::accent : colours::outline);
    g.drawRoundedRectangle (bounds, cornerSize, 1.0f);
}

juce::Font SnapPlayLookAndFeel::getTextButtonFont (juce::TextButton&, int buttonHeight)
{
    return font (juce::jmin (15.0f, static_cast<float> (buttonHeight) * 0.6f));
}

juce::Font SnapPlayLookAndFeel::getComboBoxFont (juce::ComboBox&)
{
    return font (14.0f);
}

} // namespace snapplay::ui
