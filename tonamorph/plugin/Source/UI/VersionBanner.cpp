#include "UI/VersionBanner.h"

#include "Core/Strings.h"
#include "UI/TonamorphLookAndFeel.h"

namespace tonamorph::ui
{

VersionBanner::VersionBanner()
{
    label.setFont (TonamorphLookAndFeel::font (14.0f, true));
    label.setColour (juce::Label::textColourId, colours::background);
    label.setJustificationType (juce::Justification::centredLeft);

    downloadButton.setButtonText (juce::String::fromUTF8 (strings::download));
    downloadButton.onClick = [this]
    {
        if (url.isNotEmpty())
            juce::URL (url).launchInDefaultBrowser();
    };

    dismissButton.setButtonText (juce::String::fromUTF8 (strings::dismiss));
    dismissButton.onClick = [this]
    {
        if (onDismiss != nullptr)
            onDismiss();
    };

    addAndMakeVisible (label);
    addAndMakeVisible (downloadButton);
    addAndMakeVisible (dismissButton);
    setVisible (false);
}

void VersionBanner::showUpdateAvailable (const juce::String& latestVersion, const juce::String& downloadUrl)
{
    required = false;
    url = downloadUrl;
    label.setText (strings::fill (strings::fill (strings::updateAvailable, "product", strings::productName),
                                  "version", latestVersion.toStdString()),
                   juce::dontSendNotification);
    downloadButton.setVisible (downloadUrl.isNotEmpty());
    dismissButton.setVisible (true);
    setVisible (true);
    resized();
}

void VersionBanner::showUpdateRequired (const juce::String& downloadUrl)
{
    required = true;
    url = downloadUrl;
    label.setText (juce::String::fromUTF8 (strings::updateRequired), juce::dontSendNotification);
    downloadButton.setVisible (downloadUrl.isNotEmpty());
    dismissButton.setVisible (false);
    setVisible (true);
    resized();
}

void VersionBanner::hide()
{
    setVisible (false);
}

void VersionBanner::paint (juce::Graphics& g)
{
    g.setColour (required ? colours::danger : colours::accent);
    g.fillRoundedRectangle (getLocalBounds().toFloat(), 6.0f);
}

void VersionBanner::resized()
{
    auto area = getLocalBounds().reduced (10, 4);

    if (dismissButton.isVisible())
    {
        dismissButton.setBounds (area.removeFromRight (84));
        area.removeFromRight (8);
    }

    if (downloadButton.isVisible())
    {
        downloadButton.setBounds (area.removeFromRight (100));
        area.removeFromRight (8);
    }

    label.setBounds (area);
}

} // namespace tonamorph::ui
