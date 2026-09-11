#include "UI/NpsCard.h"

#include "Core/Retention.h"
#include "Core/Strings.h"
#include "UI/TonamorphLookAndFeel.h"

namespace tonamorph::ui
{

namespace
{
    constexpr int scoreRadioGroup = 1002;

    juce::String s (const char* text) { return juce::String::fromUTF8 (text); }
}

NpsCard::NpsCard()
{
    questionLabel.setText (juce::String::fromUTF8 (strings::fill (strings::npsQuestion, "product", strings::productName).c_str()),
                           juce::dontSendNotification);
    questionLabel.setFont (TonamorphLookAndFeel::font (15.0f, true));
    questionLabel.setJustificationType (juce::Justification::centredLeft);

    for (int score = 0; score < numScores; ++score)
    {
        auto& button = scoreButtons[static_cast<size_t> (score)];
        button.setButtonText (juce::String (score));
        button.setClickingTogglesState (true);
        button.setRadioGroupId (scoreRadioGroup);
        button.onClick = [this, score] { selectScore (score); };
        addAndMakeVisible (button);
    }

    commentEditor.setTextToShowWhenEmpty (s (strings::npsCommentPlaceholder), colours::textDim);
    commentEditor.setFont (TonamorphLookAndFeel::font (13.0f));
    commentEditor.setInputRestrictions (static_cast<int> (core::maxNpsCommentLength));
    commentEditor.onReturnKey = [this]
    {
        if (sendButton.isEnabled())
            sendButton.triggerClick();
    };

    sendButton.setButtonText (s (strings::feedbackSend));
    sendButton.setEnabled (false);
    sendButton.onClick = [this]
    {
        if (onSubmit != nullptr && core::isValidNpsScore (selectedScore))
            onSubmit (selectedScore, commentEditor.getText());
    };

    dismissButton.setButtonText (s (strings::notNow));
    dismissButton.onClick = [this]
    {
        if (onDismiss != nullptr)
            onDismiss();
    };

    outcomeLabel.setFont (TonamorphLookAndFeel::font (15.0f, true));
    outcomeLabel.setColour (juce::Label::textColourId, colours::accent);
    outcomeLabel.setJustificationType (juce::Justification::centred);

    addAndMakeVisible (questionLabel);
    addAndMakeVisible (commentEditor);
    addAndMakeVisible (sendButton);
    addAndMakeVisible (dismissButton);
    addChildComponent (outcomeLabel);
    setVisible (false);
}

NpsCard::~NpsCard()
{
    stopTimer();
}

void NpsCard::showCard()
{
    stopTimer();
    selectedScore = -1;

    for (auto& button : scoreButtons)
        button.setToggleState (false, juce::dontSendNotification);

    commentEditor.clear();
    setBusy (false);
    sendButton.setEnabled (false);
    setShowingOutcome (false);
    setVisible (true);
    toFront (false);
}

void NpsCard::showOutcome (const juce::String& message, bool keepControl)
{
    stopTimer();
    setBusy (false);
    returnToQuestionAfterOutcome = keepControl;
    outcomeLabel.setText (message, juce::dontSendNotification);
    setShowingOutcome (true);
    setVisible (true);
    startTimer (outcomeVisibleMs);
}

void NpsCard::setBusy (bool busy)
{
    for (auto& button : scoreButtons)
        button.setEnabled (! busy);

    commentEditor.setEnabled (! busy);
    dismissButton.setEnabled (! busy);
    sendButton.setEnabled (! busy && core::isValidNpsScore (selectedScore));
}

void NpsCard::hideCard()
{
    stopTimer();
    setVisible (false);
}

void NpsCard::paint (juce::Graphics& g)
{
    const auto bounds = getLocalBounds().toFloat().reduced (1.0f);
    g.setColour (colours::panelLight);
    g.fillRoundedRectangle (bounds, 10.0f);
    g.setColour (colours::accent);
    g.drawRoundedRectangle (bounds, 10.0f, 1.5f);
}

void NpsCard::resized()
{
    auto area = getLocalBounds().reduced (16, 12);
    outcomeLabel.setBounds (area);

    auto headerRow = area.removeFromTop (24);
    dismissButton.setBounds (headerRow.removeFromRight (84));
    headerRow.removeFromRight (8);
    questionLabel.setBounds (headerRow);
    area.removeFromTop (10);

    auto scoreRow = area.removeFromTop (30);
    const int gap = 4;
    const int buttonWidth = (scoreRow.getWidth() - gap * (numScores - 1)) / numScores;

    for (auto& button : scoreButtons)
    {
        button.setBounds (scoreRow.removeFromLeft (buttonWidth));
        scoreRow.removeFromLeft (gap);
    }

    area.removeFromTop (10);
    auto commentRow = area.removeFromTop (30);
    sendButton.setBounds (commentRow.removeFromRight (84));
    commentRow.removeFromRight (8);
    commentEditor.setBounds (commentRow);
}

void NpsCard::timerCallback()
{
    stopTimer();

    if (returnToQuestionAfterOutcome)
        setShowingOutcome (false);
    else
        hideCard();
}

void NpsCard::selectScore (int score)
{
    selectedScore = score;
    sendButton.setEnabled (core::isValidNpsScore (selectedScore));
    commentEditor.grabKeyboardFocus();
}

void NpsCard::setShowingOutcome (bool showing)
{
    outcomeLabel.setVisible (showing);
    questionLabel.setVisible (! showing);
    commentEditor.setVisible (! showing);
    sendButton.setVisible (! showing);
    dismissButton.setVisible (! showing);

    for (auto& button : scoreButtons)
        button.setVisible (! showing);
}

} // namespace tonamorph::ui
