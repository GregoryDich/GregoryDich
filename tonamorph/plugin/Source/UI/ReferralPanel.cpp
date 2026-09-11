#include "UI/ReferralPanel.h"

#include "Core/Retention.h"
#include "Core/Strings.h"

namespace tonamorph::ui
{

namespace
{
    constexpr int referralPanelWidth = 480;
    constexpr int referralPanelHeight = 262;

    juce::String s (const char* text) { return juce::String::fromUTF8 (text); }
}

ReferralPanel::ReferralPanel()
    : PanelOverlay (referralPanelWidth, referralPanelHeight)
{
    titleLabel.setText (s (strings::referralShare), juce::dontSendNotification);
    titleLabel.setFont (TonamorphLookAndFeel::font (19.0f, true));
    titleLabel.setJustificationType (juce::Justification::centred);

    promiseLabel.setText (juce::String::fromUTF8 (core::referralPromiseLine().c_str()), juce::dontSendNotification);
    promiseLabel.setFont (TonamorphLookAndFeel::font (13.5f));
    promiseLabel.setJustificationType (juce::Justification::centred);
    promiseLabel.setColour (juce::Label::textColourId, colours::textDim);

    urlEditor.setReadOnly (true);
    urlEditor.setCaretVisible (false);
    urlEditor.setPopupMenuEnabled (true);
    urlEditor.setJustification (juce::Justification::centredLeft);
    urlEditor.setFont (TonamorphLookAndFeel::font (14.0f));
    urlEditor.setColour (juce::TextEditor::backgroundColourId, colours::background);
    urlEditor.setColour (juce::TextEditor::outlineColourId, colours::outline);
    urlEditor.setColour (juce::TextEditor::focusedOutlineColourId, colours::accentDim);
    urlEditor.setColour (juce::TextEditor::textColourId, colours::text);

    copyButton.setButtonText (s (strings::copyButton));
    copyButton.onClick = [this]
    {
        juce::SystemClipboard::copyTextToClipboard (urlEditor.getText());
        copiedLabel.setVisible (true);
        startTimer (copiedVisibleMs);
    };

    copiedLabel.setText (s (strings::copied), juce::dontSendNotification);
    copiedLabel.setFont (TonamorphLookAndFeel::font (13.0f));
    copiedLabel.setColour (juce::Label::textColourId, colours::accent);
    copiedLabel.setJustificationType (juce::Justification::centred);

    statsLabel.setFont (TonamorphLookAndFeel::font (13.0f));
    statsLabel.setJustificationType (juce::Justification::centred);
    statsLabel.setColour (juce::Label::textColourId, colours::accent);

    closeButton.setButtonText (s (strings::closeButton));
    closeButton.onClick = [this] { requestClose(); };

    addAndMakeVisible (titleLabel);
    addAndMakeVisible (promiseLabel);
    addAndMakeVisible (urlEditor);
    addAndMakeVisible (copyButton);
    addChildComponent (copiedLabel);
    addChildComponent (statsLabel);
    addAndMakeVisible (closeButton);
}

ReferralPanel::~ReferralPanel()
{
    stopTimer();
}

void ReferralPanel::setReferral (const cloud::ReferralInfo& referral)
{
    urlEditor.setText (referral.url, false);

    const bool hasStats = referral.friendsJoined > 0 || referral.morphsEarned > 0;
    statsLabel.setVisible (hasStats);

    if (hasStats)
        statsLabel.setText (juce::String (strings::fill (strings::fill (strings::referralStats, "friends",
                                                                        std::to_string (referral.friendsJoined)),
                                                         "morphs", std::to_string (referral.morphsEarned))),
                            juce::dontSendNotification);
}

void ReferralPanel::resized()
{
    auto area = getPanelBounds().reduced (28, 22);

    titleLabel.setBounds (area.removeFromTop (30));
    area.removeFromTop (6);
    promiseLabel.setBounds (area.removeFromTop (22));
    area.removeFromTop (14);

    auto urlRow = area.removeFromTop (32);
    copyButton.setBounds (urlRow.removeFromRight (80));
    urlRow.removeFromRight (8);
    urlEditor.setBounds (urlRow);
    area.removeFromTop (6);
    copiedLabel.setBounds (area.removeFromTop (20));
    statsLabel.setBounds (area.removeFromTop (22));

    closeButton.setBounds (area.removeFromBottom (30).withSizeKeepingCentre (120, 30));
}

void ReferralPanel::timerCallback()
{
    stopTimer();
    copiedLabel.setVisible (false);
}

} // namespace tonamorph::ui
