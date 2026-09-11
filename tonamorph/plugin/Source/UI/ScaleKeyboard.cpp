#include "UI/ScaleKeyboard.h"

#include "UI/TonamorphLookAndFeel.h"

namespace tonamorph::ui
{

namespace
{
    constexpr int frameIntervalMs = 33;
    constexpr double fadeInMs = 150.0;
    constexpr double fadeOutMs = 500.0;
} // namespace

ScaleKeyboard::ScaleKeyboard (juce::MidiKeyboardState& stateToUse, Orientation orientationToUse)
    : juce::MidiKeyboardComponent (stateToUse, orientationToUse)
{
    ticker.onTick = [this]
    {
        if (glowMask != 0 && juce::Time::getMillisecondCounterHiRes() - glowStartMs >= glowDurationMs)
        {
            glowMask = 0;
            ticker.stopTimer();
        }

        repaint();
    };
}

ScaleKeyboard::~ScaleKeyboard()
{
    ticker.stopTimer();
}

void ScaleKeyboard::glowPitchClasses (const std::vector<int>& pitchClasses, int durationMs)
{
    glowMask = 0;

    for (const int pitchClass : pitchClasses)
        if (pitchClass >= 0 && pitchClass < 12)
            glowMask = static_cast<std::uint16_t> (glowMask | (1u << pitchClass));

    if (glowMask == 0 || durationMs <= 0)
        return;

    glowStartMs = juce::Time::getMillisecondCounterHiRes();
    glowDurationMs = durationMs;
    ticker.startTimer (frameIntervalMs);
    repaint();
}

void ScaleKeyboard::setHighlightedNote (int midiNote)
{
    highlightedNote = midiNote;
    repaint();
}

void ScaleKeyboard::clearOverlays()
{
    glowMask = 0;
    highlightedNote = -1;
    ticker.stopTimer();
    repaint();
}

float ScaleKeyboard::glowAlphaNow() const
{
    if (glowMask == 0)
        return 0.0f;

    const double elapsed = juce::Time::getMillisecondCounterHiRes() - glowStartMs;
    const double remaining = glowDurationMs - elapsed;
    const double alpha = juce::jmin (elapsed / fadeInMs, remaining / fadeOutMs, 1.0);
    return static_cast<float> (juce::jlimit (0.0, 1.0, alpha));
}

void ScaleKeyboard::drawOverlays (int midiNoteNumber, juce::Graphics& g, juce::Rectangle<float> area)
{
    const auto alpha = glowAlphaNow();

    if (alpha > 0.0f && (glowMask & (1u << (midiNoteNumber % 12))) != 0)
    {
        g.setColour (colours::accent.withAlpha (0.55f * alpha));
        g.fillRect (area);
    }

    if (midiNoteNumber == highlightedNote)
    {
        g.setColour (colours::accent.withAlpha (0.8f));
        g.fillRect (area);
        g.setColour (colours::background);

        const auto dot = juce::Rectangle<float> (8.0f, 8.0f).withCentre ({ area.getCentreX(), area.getBottom() - 14.0f });
        g.fillEllipse (dot);
    }
}

void ScaleKeyboard::drawWhiteNote (int midiNoteNumber, juce::Graphics& g, juce::Rectangle<float> area, bool isDown,
                                   bool isOver, juce::Colour lineColour, juce::Colour textColour)
{
    juce::MidiKeyboardComponent::drawWhiteNote (midiNoteNumber, g, area, isDown, isOver, lineColour, textColour);
    drawOverlays (midiNoteNumber, g, area);
}

void ScaleKeyboard::drawBlackNote (int midiNoteNumber, juce::Graphics& g, juce::Rectangle<float> area, bool isDown,
                                   bool isOver, juce::Colour noteFillColour)
{
    juce::MidiKeyboardComponent::drawBlackNote (midiNoteNumber, g, area, isDown, isOver, noteFillColour);
    drawOverlays (midiNoteNumber, g, area);
}

} // namespace tonamorph::ui
