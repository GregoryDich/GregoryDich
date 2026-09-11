#include "UI/FeedbackBar.h"

#include "Core/FeedbackPayload.h"
#include "Core/Strings.h"
#include "UI/TonamorphLookAndFeel.h"

namespace tonamorph::ui
{

namespace
{
    constexpr int outcomeVisibleMs = 3500;

    /** Reason labels in core::feedbackReasons order. */
    const char* reasonLabel (int index)
    {
        switch (index)
        {
            case 0: return strings::feedbackReasonBleed;
            case 1: return strings::feedbackReasonWrongKey;
            case 2: return strings::feedbackReasonMidiOff;
            case 3: return strings::feedbackReasonClicks;
            case 4: return strings::feedbackReasonSlow;
            default: return strings::feedbackReasonOther;
        }
    }
} // namespace

FeedbackBar::FeedbackBar()
{
    promptLabel.setText (juce::String::fromUTF8 (strings::feedbackPrompt), juce::dontSendNotification);
    promptLabel.setFont (TonamorphLookAndFeel::font (13.0f));
    promptLabel.setColour (juce::Label::textColourId, colours::textDim);
    promptLabel.setJustificationType (juce::Justification::centredRight);

    upButton.setButtonText (juce::String::fromUTF8 (strings::feedbackUp));
    upButton.onClick = [this]
    {
        if (onSubmit != nullptr)
            onSubmit (true, {}, {});
    };

    downButton.setButtonText (juce::String::fromUTF8 (strings::feedbackDown));
    downButton.onClick = [this] { setMode (Mode::Reasons); };

    for (int i = 0; i < static_cast<int> (core::feedbackReasons.size()); ++i)
        reasonBox.addItem (juce::String::fromUTF8 (reasonLabel (i)), i + 1);

    reasonBox.setSelectedId (1, juce::dontSendNotification);

    noteEditor.setTextToShowWhenEmpty (juce::String::fromUTF8 (strings::feedbackNotePlaceholder), colours::textDim);
    noteEditor.setFont (TonamorphLookAndFeel::font (13.0f));
    noteEditor.setInputRestrictions (noteLimit);
    noteEditor.onReturnKey = [this] { sendDown(); };

    sendButton.setButtonText (juce::String::fromUTF8 (strings::feedbackSend));
    sendButton.onClick = [this] { sendDown(); };

    outcomeLabel.setFont (TonamorphLookAndFeel::font (13.0f));
    outcomeLabel.setColour (juce::Label::textColourId, colours::accent);
    outcomeLabel.setJustificationType (juce::Justification::centredRight);

    addChildComponent (promptLabel);
    addChildComponent (upButton);
    addChildComponent (downButton);
    addChildComponent (reasonBox);
    addChildComponent (noteEditor);
    addChildComponent (sendButton);
    addChildComponent (outcomeLabel);
    setVisible (false);
}

FeedbackBar::~FeedbackBar()
{
    stopTimer();
}

void FeedbackBar::showPrompt()
{
    stopTimer();
    setBusy (false);
    noteEditor.clear();
    reasonBox.setSelectedId (1, juce::dontSendNotification);
    setMode (Mode::Prompt);
    setVisible (true);
}

void FeedbackBar::showOutcome (const juce::String& message, bool keepControl)
{
    stopTimer();
    setBusy (false);
    returnToPromptAfterOutcome = keepControl;
    outcomeLabel.setText (message, juce::dontSendNotification);
    setMode (Mode::Outcome);
    setVisible (true);
    startTimer (outcomeVisibleMs);
}

void FeedbackBar::setBusy (bool busy)
{
    juce::Component* controls[] = { &upButton, &downButton, &reasonBox, &noteEditor, &sendButton };

    for (auto* component : controls)
        component->setEnabled (! busy);
}

void FeedbackBar::hideBar()
{
    stopTimer();
    setVisible (false);
}

void FeedbackBar::resized()
{
    auto area = getLocalBounds();

    // Everything hangs off the right edge, next to the export buttons.
    if (mode == Mode::Prompt)
    {
        downButton.setBounds (area.removeFromRight (92));
        area.removeFromRight (6);
        upButton.setBounds (area.removeFromRight (72));
        area.removeFromRight (10);
        promptLabel.setBounds (area);
    }
    else if (mode == Mode::Reasons)
    {
        sendButton.setBounds (area.removeFromRight (70));
        area.removeFromRight (6);
        noteEditor.setBounds (area.removeFromRight (juce::jmin (260, juce::jmax (120, area.getWidth() - 180))));
        area.removeFromRight (6);
        reasonBox.setBounds (area.removeFromRight (150));
    }
    else
    {
        outcomeLabel.setBounds (area);
    }
}

void FeedbackBar::timerCallback()
{
    stopTimer();

    if (returnToPromptAfterOutcome)
        showPrompt();
    else
        hideBar();
}

void FeedbackBar::setMode (Mode newMode)
{
    mode = newMode;
    promptLabel.setVisible (mode == Mode::Prompt);
    upButton.setVisible (mode == Mode::Prompt);
    downButton.setVisible (mode == Mode::Prompt);
    reasonBox.setVisible (mode == Mode::Reasons);
    noteEditor.setVisible (mode == Mode::Reasons);
    sendButton.setVisible (mode == Mode::Reasons);
    outcomeLabel.setVisible (mode == Mode::Outcome);
    resized();

    if (mode == Mode::Reasons)
        noteEditor.grabKeyboardFocus();
}

void FeedbackBar::sendDown()
{
    const int index = juce::jlimit (0, static_cast<int> (core::feedbackReasons.size()) - 1, reasonBox.getSelectedId() - 1);

    if (onSubmit != nullptr)
        onSubmit (false, core::feedbackReasons[static_cast<size_t> (index)], noteEditor.getText());
}

} // namespace tonamorph::ui
