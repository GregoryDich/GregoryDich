#include "PluginEditor.h"

#include "Export/DragExport.h"
#include "Export/FscExporter.h"
#include "Export/MidiExporter.h"

namespace snapplay
{

//==============================================================================
PaywallPrompt::PaywallPrompt()
{
    addAndMakeVisible (titleLabel);
    addAndMakeVisible (messageLabel);
    addAndMakeVisible (buyPackButton);
    addAndMakeVisible (subscribeButton);
    addAndMakeVisible (dismissButton);
}

void PaywallPrompt::setPlans (const std::vector<cloud::PlanInfo>& newPlans)
{
    plans = newPlans;
    rebuildMessage();
}

void PaywallPrompt::setFreeCredits (int credits)
{
    freeCredits = credits;
    rebuildMessage();
}

void PaywallPrompt::paint (juce::Graphics& g)
{
    g.fillAll (getLookAndFeel().findColour (juce::ResizableWindow::backgroundColourId).withAlpha (0.95f));
}

void PaywallPrompt::resized()
{
}

void PaywallPrompt::rebuildMessage()
{
}

//==============================================================================
LoginOverlay::LoginOverlay()
{
    addAndMakeVisible (titleLabel);
    addAndMakeVisible (emailLabel);
    addAndMakeVisible (emailEditor);
    addAndMakeVisible (passwordLabel);
    addAndMakeVisible (passwordEditor);
    addAndMakeVisible (loginButton);
    addAndMakeVisible (statusLabel);
    addAndMakeVisible (signupLink);
}

void LoginOverlay::setBusy (bool busy)
{
    juce::ignoreUnused (busy);
}

void LoginOverlay::setErrorMessage (const juce::String& message)
{
    statusLabel.setText (message, juce::dontSendNotification);
}

void LoginOverlay::clearForm()
{
    emailEditor.clear();
    passwordEditor.clear();
    statusLabel.setText ({}, juce::dontSendNotification);
}

void LoginOverlay::paint (juce::Graphics& g)
{
    g.fillAll (getLookAndFeel().findColour (juce::ResizableWindow::backgroundColourId));
}

void LoginOverlay::resized()
{
}

void LoginOverlay::submit()
{
}

//==============================================================================
DropZone::DropZone()
{
    addAndMakeVisible (messageLabel);
}

void DropZone::setMessage (const juce::String& message)
{
    messageLabel.setText (message, juce::dontSendNotification);
}

void DropZone::setHighlighted (bool shouldHighlight)
{
    highlighted = shouldHighlight;
    repaint();
}

void DropZone::setEnabledForDrop (bool enabled)
{
    dropEnabled = enabled;
    repaint();
}

void DropZone::paint (juce::Graphics& g)
{
    juce::ignoreUnused (g);
}

void DropZone::resized()
{
    messageLabel.setBounds (getLocalBounds());
}

void DropZone::mouseUp (const juce::MouseEvent& event)
{
    juce::ignoreUnused (event);
}

//==============================================================================
ExportDragButton::ExportDragButton (const juce::String& buttonText)
    : juce::TextButton (buttonText)
{
}

void ExportDragButton::mouseDrag (const juce::MouseEvent& event)
{
    juce::ignoreUnused (event);
}

void ExportDragButton::mouseUp (const juce::MouseEvent& event)
{
    juce::TextButton::mouseUp (event);
    dragStarted = false;
}

//==============================================================================
SnapPlayAudioProcessorEditor::SnapPlayAudioProcessorEditor (SnapPlayAudioProcessor& processorToUse)
    : juce::AudioProcessorEditor (processorToUse),
      processor (processorToUse),
      progressBar (progressValue),
      dragMidiButton ("Drag .mid"),
      dragFscButton ("Drag .fsc"),
      keyboard (processorToUse.getKeyboardState(), juce::MidiKeyboardComponent::horizontalKeyboard)
{
    setSize (defaultWidth, defaultHeight);

    processor.getJobClient().addChangeListener (this);
    processor.getAuthManager().addListener (this);
}

SnapPlayAudioProcessorEditor::~SnapPlayAudioProcessorEditor()
{
    if (plansRequest != cloud::ApiClient::invalidRequest)
        processor.getApiClient().cancel (plansRequest);

    processor.getAuthManager().removeListener (this);
    processor.getJobClient().removeChangeListener (this);
}

void SnapPlayAudioProcessorEditor::paint (juce::Graphics& g)
{
    g.fillAll (getLookAndFeel().findColour (juce::ResizableWindow::backgroundColourId));
}

void SnapPlayAudioProcessorEditor::resized()
{
}

//==============================================================================
bool SnapPlayAudioProcessorEditor::isInterestedInFileDrag (const juce::StringArray& files)
{
    juce::ignoreUnused (files);
    return false;
}

void SnapPlayAudioProcessorEditor::fileDragEnter (const juce::StringArray& files, int x, int y)
{
    juce::ignoreUnused (files, x, y);
}

void SnapPlayAudioProcessorEditor::fileDragExit (const juce::StringArray& files)
{
    juce::ignoreUnused (files);
}

void SnapPlayAudioProcessorEditor::filesDropped (const juce::StringArray& files, int x, int y)
{
    juce::ignoreUnused (files, x, y);
}

//==============================================================================
void SnapPlayAudioProcessorEditor::changeListenerCallback (juce::ChangeBroadcaster* source)
{
    juce::ignoreUnused (source);
}

void SnapPlayAudioProcessorEditor::authStateChanged (cloud::AuthManager&)
{
}

void SnapPlayAudioProcessorEditor::balanceChanged (cloud::AuthManager&, const cloud::CreditBalance& balance)
{
    juce::ignoreUnused (balance);
}

void SnapPlayAudioProcessorEditor::authError (cloud::AuthManager&, const cloud::ApiError& error)
{
    juce::ignoreUnused (error);
}

void SnapPlayAudioProcessorEditor::timerCallback()
{
}

void SnapPlayAudioProcessorEditor::updateFromProcessor()
{
}

void SnapPlayAudioProcessorEditor::updateCreditsLabel()
{
}

void SnapPlayAudioProcessorEditor::updateJobStatus()
{
}

void SnapPlayAudioProcessorEditor::updateDetectedKeyAndBpm()
{
}

void SnapPlayAudioProcessorEditor::updateCategoryButtons()
{
}

void SnapPlayAudioProcessorEditor::showLoginOverlay (bool show)
{
    juce::ignoreUnused (show);
}

void SnapPlayAudioProcessorEditor::showPaywall (bool show)
{
    juce::ignoreUnused (show);
}

void SnapPlayAudioProcessorEditor::openFileChooser()
{
}

void SnapPlayAudioProcessorEditor::setupKnob (juce::Slider& slider, juce::Label& label, const juce::String& text)
{
    juce::ignoreUnused (slider, label, text);
}

} // namespace snapplay
