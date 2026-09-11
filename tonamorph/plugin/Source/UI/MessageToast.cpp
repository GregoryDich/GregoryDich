#include "UI/MessageToast.h"

#include "UI/TonamorphLookAndFeel.h"

namespace tonamorph::ui
{

MessageToast::MessageToast()
{
    setInterceptsMouseClicks (false, false);
    label.setJustificationType (juce::Justification::centred);
    label.setFont (TonamorphLookAndFeel::font (15.0f, true));
    label.setColour (juce::Label::textColourId, colours::background);
    label.setInterceptsMouseClicks (false, false);
    addAndMakeVisible (label);
    setVisible (false);
}

MessageToast::~MessageToast()
{
    stopTimer();
}

void MessageToast::show (const juce::String& text, int durationMs)
{
    label.setText (text, juce::dontSendNotification);
    alpha = 1.0f;
    hideAtMs = durationMs > 0 ? juce::Time::getMillisecondCounterHiRes() + durationMs : 0.0;
    setAlpha (1.0f);
    setVisible (true);
    toFront (false);

    if (hideAtMs > 0.0)
        startTimer (frameIntervalMs);
    else
        stopTimer();

    repaint();
}

void MessageToast::hide()
{
    stopTimer();
    hideAtMs = 0.0;
    setVisible (false);
}

bool MessageToast::isShowing (const juce::String& text) const
{
    return isVisible() && label.getText() == text;
}

void MessageToast::paint (juce::Graphics& g)
{
    const auto bounds = getLocalBounds().toFloat().reduced (1.0f);
    g.setColour (colours::accent);
    g.fillRoundedRectangle (bounds, 8.0f);
}

void MessageToast::resized()
{
    label.setBounds (getLocalBounds().reduced (12, 2));
}

void MessageToast::timerCallback()
{
    const double remaining = hideAtMs - juce::Time::getMillisecondCounterHiRes();

    if (remaining <= 0.0)
    {
        hide();
        return;
    }

    alpha = static_cast<float> (juce::jlimit (0.0, 1.0, remaining / fadeMs));
    setAlpha (alpha);
}

} // namespace tonamorph::ui
