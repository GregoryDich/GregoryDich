#include "UI/AboutOverlay.h"

#include "Core/Strings.h"

namespace tonamorph::ui
{

namespace
{
    constexpr int aboutPanelWidth = 660;
    constexpr int aboutPanelHeight = 540;

    juce::String s (const char* text) { return juce::String::fromUTF8 (text); }
}

AboutOverlay::AboutOverlay()
    : PanelOverlay (aboutPanelWidth, aboutPanelHeight),
      websiteLink (juce::String (JucePlugin_ManufacturerWebsite).trimCharactersAtEnd ("/"),
                   juce::URL (JucePlugin_ManufacturerWebsite))
{
    titleLabel.setText (s (strings::productName), juce::dontSendNotification);
    titleLabel.setFont (TonamorphLookAndFeel::font (22.0f, true));

    versionLabel.setText (juce::String (strings::fill (strings::aboutVersion, "version", TONAMORPH_VERSION_STRING)),
                          juce::dontSendNotification);
    versionLabel.setFont (TonamorphLookAndFeel::font (13.0f));
    versionLabel.setColour (juce::Label::textColourId, colours::textDim);

    websiteLink.setFont (TonamorphLookAndFeel::font (13.0f), false);
    websiteLink.setJustificationType (juce::Justification::centredLeft);
    websiteLink.setColour (juce::HyperlinkButton::textColourId, colours::accent);

    crashReportsToggle.setButtonText (s (strings::crashReportsOptIn));
    crashReportsToggle.onClick = [this]
    {
        if (onCrashReportingChanged != nullptr)
            onCrashReportingChanged (crashReportsToggle.getToggleState());
    };

    noticesLabel.setText (s (strings::thirdPartyNotices), juce::dontSendNotification);
    noticesLabel.setFont (TonamorphLookAndFeel::font (14.0f, true));

    noticesEditor.setMultiLine (true, false);
    noticesEditor.setReadOnly (true);
    noticesEditor.setCaretVisible (false);
    noticesEditor.setScrollbarsShown (true);
    noticesEditor.setPopupMenuEnabled (true);
    noticesEditor.setFont (juce::FontOptions (juce::Font::getDefaultMonospacedFontName(), 12.0f, juce::Font::plain));
    noticesEditor.setColour (juce::TextEditor::backgroundColourId, colours::background);
    noticesEditor.setColour (juce::TextEditor::outlineColourId, colours::outline);
    noticesEditor.setColour (juce::TextEditor::focusedOutlineColourId, colours::accentDim);
    noticesEditor.setColour (juce::TextEditor::textColourId, colours::text);

    copyButton.setButtonText (s (strings::copyButton));
    copyButton.onClick = [this]
    {
        juce::SystemClipboard::copyTextToClipboard (noticesEditor.getText());
        copiedLabel.setVisible (true);
        startTimer (copiedVisibleMs);
    };

    copiedLabel.setText (s (strings::copied), juce::dontSendNotification);
    copiedLabel.setFont (TonamorphLookAndFeel::font (13.0f));
    copiedLabel.setColour (juce::Label::textColourId, colours::accent);
    copiedLabel.setJustificationType (juce::Justification::centredRight);

    closeButton.setButtonText (s (strings::closeButton));
    closeButton.onClick = [this] { requestClose(); };

    addAndMakeVisible (titleLabel);
    addAndMakeVisible (versionLabel);
    addAndMakeVisible (websiteLink);
    addAndMakeVisible (crashReportsToggle);
    addAndMakeVisible (noticesLabel);
    addAndMakeVisible (noticesEditor);
    addAndMakeVisible (copyButton);
    addChildComponent (copiedLabel);
    addAndMakeVisible (closeButton);
}

AboutOverlay::~AboutOverlay()
{
    stopTimer();
}

void AboutOverlay::setNoticesText (const juce::String& text)
{
    noticesEditor.setText (text, false);
    noticesEditor.moveCaretToTop (false);
}

void AboutOverlay::setCrashReportingEnabled (bool enabled)
{
    crashReportsToggle.setToggleState (enabled, juce::dontSendNotification);
}

void AboutOverlay::resized()
{
    auto area = getPanelBounds().reduced (24, 20);

    auto titleRow = area.removeFromTop (30);
    versionLabel.setBounds (titleRow.removeFromRight (160));
    titleLabel.setBounds (titleRow);
    websiteLink.setBounds (area.removeFromTop (22));
    area.removeFromTop (6);
    crashReportsToggle.setBounds (area.removeFromTop (24));
    area.removeFromTop (10);

    auto footer = area.removeFromBottom (30);
    closeButton.setBounds (footer.removeFromRight (90));
    footer.removeFromRight (8);
    copyButton.setBounds (footer.removeFromRight (80));
    footer.removeFromRight (8);
    copiedLabel.setBounds (footer.removeFromRight (100));
    area.removeFromBottom (10);

    noticesLabel.setBounds (area.removeFromTop (20));
    area.removeFromTop (4);
    noticesEditor.setBounds (area);
}

void AboutOverlay::timerCallback()
{
    stopTimer();
    copiedLabel.setVisible (false);
}

} // namespace tonamorph::ui
