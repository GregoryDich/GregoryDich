#include "PluginEditor.h"

#include "Cloud/UploadEncoder.h"
#include "Export/DragExport.h"
#include "Export/FscExporter.h"
#include "Export/MidiExporter.h"

#include <iterator>

namespace snapplay
{

namespace colours = ui::colours;
using ui::SnapPlayLookAndFeel;

namespace
{
    constexpr int windowMargin = 16;
    constexpr int headerHeight = 44;
    constexpr int dragStartDistancePx = 8;
    constexpr int balanceRefreshIntervalMs = 60'000;
    constexpr int paywallPollIntervalMs = 5000;
    constexpr int lowestKeyboardNote = 24;
    constexpr int highestKeyboardNote = 108;
    constexpr int numWhiteKeys = 50;   ///< white keys between lowestKeyboardNote and highestKeyboardNote
    constexpr int categoryRadioGroup = 1001;
    constexpr int middleCOctave = 3;

    juce::String emDash()   { return juce::String::charToString (0x2014); }
    juce::String ellipsis() { return juce::String::charToString (0x2026); }

    juce::String defaultDropMessage()
    {
        return "Drop a WAV, AIFF, FLAC, MP3 or OGG file here (first 60 s are used) " + emDash() + " or click to browse";
    }

    bool hasSupportedExtension (const juce::String& path)
    {
        static const juce::StringArray extensions { ".wav", ".aif", ".aiff", ".flac", ".mp3", ".ogg" };
        return extensions.contains (juce::File::createFileWithoutCheckingPath (path).getFileExtension().toLowerCase());
    }

    juce::File firstSupportedFile (const juce::StringArray& files)
    {
        for (const auto& path : files)
            if (hasSupportedExtension (path))
                return juce::File (path);

        return {};
    }

    juce::String formatPrice (double usd)
    {
        const auto cents = juce::roundToInt (usd * 100.0);

        if (cents % 100 == 0)
            return "$" + juce::String (cents / 100);

        return "$" + juce::String (usd, 2);
    }

    juce::String formatBpm (double bpm)
    {
        const auto tenths = juce::roundToInt (bpm * 10.0);
        const auto text = tenths % 10 == 0 ? juce::String (tenths / 10) : juce::String (bpm, 1);
        return text + " BPM";
    }

    juce::String describeError (const cloud::ApiError& error)
    {
        if (error.message.isNotEmpty())
            return error.message;

        if (error.code.isNotEmpty())
            return "Request failed (" + error.code + ")";

        return "Request failed";
    }

    juce::String noteNameFor (int midiNote)
    {
        return juce::MidiMessage::getMidiNoteName (midiNote, true, true, middleCOctave);
    }

    /** Accepts "C3", "F#2", "Bb1" or a plain number. */
    double noteNumberFromText (const juce::String& text)
    {
        const auto trimmed = text.trim().toUpperCase();

        if (trimmed.isEmpty() || ! juce::CharacterFunctions::isLetter (trimmed[0]))
            return trimmed.getDoubleValue();

        int pitchClass = juce::String ("C D EF G A B").indexOfChar (trimmed[0]);

        if (pitchClass < 0)
            return 0.0;

        int octaveStart = 1;

        if (trimmed.length() > 1 && trimmed[1] == '#')
        {
            ++pitchClass;
            ++octaveStart;
        }
        else if (trimmed.length() > 1 && trimmed[1] == 'B' && trimmed.length() > 2)
        {
            --pitchClass;
            ++octaveStart;
        }

        const int octave = trimmed.substring (octaveStart).getIntValue();
        return (octave - middleCOctave + 5) * 12 + pitchClass;
    }
} // namespace

//==============================================================================
PaywallPrompt::PaywallPrompt()
{
    titleLabel.setText ("You're out of credits", juce::dontSendNotification);
    titleLabel.setJustificationType (juce::Justification::centred);
    titleLabel.setFont (SnapPlayLookAndFeel::font (22.0f, true));

    messageLabel.setJustificationType (juce::Justification::centred);
    messageLabel.setFont (SnapPlayLookAndFeel::font (15.0f));

    dismissButton.setButtonText ("Not now");

    onCheckout = [] (const cloud::PlanInfo& plan)
    {
        if (plan.checkoutUrl.has_value())
            juce::URL (*plan.checkoutUrl).launchInDefaultBrowser();
    };

    buyPackButton.onClick = [this]
    {
        if (const auto* plan = findPlan (false); plan != nullptr && onCheckout != nullptr)
            onCheckout (*plan);
    };

    subscribeButton.onClick = [this]
    {
        if (const auto* plan = findPlan (true); plan != nullptr && onCheckout != nullptr)
            onCheckout (*plan);
    };

    dismissButton.onClick = [this]
    {
        if (onDismiss != nullptr)
            onDismiss();
    };

    addAndMakeVisible (titleLabel);
    addAndMakeVisible (messageLabel);
    addAndMakeVisible (buyPackButton);
    addAndMakeVisible (subscribeButton);
    addAndMakeVisible (dismissButton);

    rebuildMessage();
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
    g.fillAll (colours::background.withAlpha (0.92f));

    const auto panel = getPanelBounds().toFloat();
    g.setColour (colours::panel);
    g.fillRoundedRectangle (panel, 10.0f);
    g.setColour (colours::accent);
    g.drawRoundedRectangle (panel, 10.0f, 1.5f);
}

void PaywallPrompt::resized()
{
    auto area = getPanelBounds().reduced (24, 20);

    titleLabel.setBounds (area.removeFromTop (32));
    area.removeFromTop (8);
    messageLabel.setBounds (area.removeFromTop (64));
    area.removeFromTop (12);

    auto buttonRow = area.removeFromTop (36);
    const int visibleButtons = (buyPackButton.isVisible() ? 1 : 0) + (subscribeButton.isVisible() ? 1 : 0);

    if (visibleButtons > 0)
    {
        const int gap = 12;
        const int buttonWidth = (buttonRow.getWidth() - gap * (visibleButtons - 1)) / visibleButtons;

        for (auto* button : { &buyPackButton, &subscribeButton })
        {
            if (! button->isVisible())
                continue;

            button->setBounds (buttonRow.removeFromLeft (buttonWidth));
            buttonRow.removeFromLeft (gap);
        }
    }

    area.removeFromTop (12);
    dismissButton.setBounds (area.removeFromTop (28).withSizeKeepingCentre (120, 28));
}

void PaywallPrompt::rebuildMessage()
{
    const auto* pack = findPlan (false);
    const auto* subscription = findPlan (true);

    juce::StringArray offers;

    if (pack != nullptr)
        offers.add ("unlock " + juce::String (pack->credits) + " more for " + formatPrice (pack->priceUsd));

    if (subscription != nullptr)
        offers.add ("subscribe for " + formatPrice (subscription->priceUsd) + "/mo");

    auto message = "You've used your " + juce::String (freeCredits) + " free credits";
    message += offers.isEmpty() ? ". Visit snapplay.ai to add more."
                                : " " + emDash() + " " + offers.joinIntoString (", or ") + ".";
    messageLabel.setText (message, juce::dontSendNotification);

    buyPackButton.setVisible (pack != nullptr);

    if (pack != nullptr)
        buyPackButton.setButtonText (pack->name + " " + emDash() + " " + formatPrice (pack->priceUsd));

    subscribeButton.setVisible (subscription != nullptr);

    if (subscription != nullptr)
        subscribeButton.setButtonText (subscription->name + " " + emDash() + " " + formatPrice (subscription->priceUsd) + "/mo");

    resized();
}

const cloud::PlanInfo* PaywallPrompt::findPlan (bool subscription) const
{
    for (const auto& plan : plans)
    {
        if (! plan.checkoutUrl.has_value() || plan.checkoutUrl->isEmpty())
            continue;

        if (plan.isSubscription() == subscription && (subscription || plan.credits > 0))
            return &plan;
    }

    return nullptr;
}

juce::Rectangle<int> PaywallPrompt::getPanelBounds() const
{
    return getLocalBounds().withSizeKeepingCentre (juce::jmin (480, getWidth() - 32), 268);
}

//==============================================================================
LoginOverlay::LoginOverlay()
    : signupLink ("Create an account at snapplay.ai", juce::URL ("https://snapplay.ai/signup"))
{
    titleLabel.setText ("Sign in to SnapPlay AI", juce::dontSendNotification);
    titleLabel.setJustificationType (juce::Justification::centred);
    titleLabel.setFont (SnapPlayLookAndFeel::font (22.0f, true));

    emailLabel.setText ("Email", juce::dontSendNotification);
    emailLabel.setFont (SnapPlayLookAndFeel::font (13.0f));
    emailEditor.setTextToShowWhenEmpty ("you@example.com", colours::textDim);
    emailEditor.setFont (SnapPlayLookAndFeel::font (15.0f));
    emailEditor.onReturnKey = [this] { passwordEditor.grabKeyboardFocus(); };

    passwordLabel.setText ("Password", juce::dontSendNotification);
    passwordLabel.setFont (SnapPlayLookAndFeel::font (13.0f));
    passwordEditor.setPasswordCharacter (0x2022);
    passwordEditor.setFont (SnapPlayLookAndFeel::font (15.0f));
    passwordEditor.onReturnKey = [this] { submit(); };

    loginButton.setButtonText ("Sign in");
    loginButton.onClick = [this] { submit(); };

    statusLabel.setJustificationType (juce::Justification::centred);
    statusLabel.setFont (SnapPlayLookAndFeel::font (13.0f));
    statusLabel.setColour (juce::Label::textColourId, colours::danger);

    signupLink.setJustificationType (juce::Justification::centred);
    signupLink.setFont (SnapPlayLookAndFeel::font (13.0f), false);

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
    emailEditor.setEnabled (! busy);
    passwordEditor.setEnabled (! busy);
    loginButton.setEnabled (! busy);
    loginButton.setButtonText (busy ? "Signing in" + ellipsis() : "Sign in");
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
    g.fillAll (colours::background);

    const auto panel = getPanelBounds().toFloat();
    g.setColour (colours::panel);
    g.fillRoundedRectangle (panel, 10.0f);
    g.setColour (colours::outline);
    g.drawRoundedRectangle (panel, 10.0f, 1.0f);
}

void LoginOverlay::resized()
{
    auto area = getPanelBounds().reduced (28, 24);

    titleLabel.setBounds (area.removeFromTop (32));
    area.removeFromTop (16);

    emailLabel.setBounds (area.removeFromTop (18));
    emailEditor.setBounds (area.removeFromTop (30));
    area.removeFromTop (10);

    passwordLabel.setBounds (area.removeFromTop (18));
    passwordEditor.setBounds (area.removeFromTop (30));
    area.removeFromTop (16);

    loginButton.setBounds (area.removeFromTop (34));
    area.removeFromTop (8);
    statusLabel.setBounds (area.removeFromTop (36));
    signupLink.setBounds (area.removeFromTop (22));
}

void LoginOverlay::submit()
{
    const auto email = emailEditor.getText().trim();
    const auto password = passwordEditor.getText();

    if (email.isEmpty() || ! email.containsChar ('@') || password.isEmpty())
    {
        setErrorMessage ("Enter your email address and password.");
        return;
    }

    setErrorMessage ({});

    if (onLogin != nullptr)
        onLogin (email, password);
}

juce::Rectangle<int> LoginOverlay::getPanelBounds() const
{
    return getLocalBounds().withSizeKeepingCentre (juce::jmin (380, getWidth() - 32), 340);
}

//==============================================================================
DropZone::DropZone()
{
    messageLabel.setJustificationType (juce::Justification::centred);
    messageLabel.setFont (SnapPlayLookAndFeel::font (15.0f));
    messageLabel.setInterceptsMouseClicks (false, false);
    setMouseCursor (juce::MouseCursor::PointingHandCursor);
    setMessage (defaultDropMessage());
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
    setMouseCursor (enabled ? juce::MouseCursor::PointingHandCursor : juce::MouseCursor::NormalCursor);
    messageLabel.setColour (juce::Label::textColourId, enabled ? colours::text : colours::textDim);
    repaint();
}

void DropZone::paint (juce::Graphics& g)
{
    const auto bounds = getLocalBounds().toFloat().reduced (2.0f);
    constexpr float cornerSize = 8.0f;

    g.setColour (highlighted ? colours::accent.withAlpha (0.18f) : colours::panel);
    g.fillRoundedRectangle (bounds, cornerSize);

    juce::Path outline;
    outline.addRoundedRectangle (bounds, cornerSize);

    juce::Path dashed;
    const float dashLengths[] = { 7.0f, 5.0f };
    juce::PathStrokeType (1.5f).createDashedStroke (dashed, outline, dashLengths, 2);

    g.setColour (highlighted ? colours::accent : (dropEnabled ? colours::textDim : colours::outline));
    g.fillPath (dashed);
}

void DropZone::resized()
{
    messageLabel.setBounds (getLocalBounds().reduced (12, 4));
}

void DropZone::mouseUp (const juce::MouseEvent& event)
{
    if (dropEnabled && onBrowse != nullptr && contains (event.getPosition()))
        onBrowse();
}

//==============================================================================
ExportDragButton::ExportDragButton (const juce::String& buttonText)
    : juce::TextButton (buttonText)
{
}

void ExportDragButton::mouseDown (const juce::MouseEvent& event)
{
    dragStarted = false;
    juce::TextButton::mouseDown (event);
}

void ExportDragButton::mouseDrag (const juce::MouseEvent& event)
{
    if (dragStarted || ! isEnabled() || event.getDistanceFromDragStart() < dragStartDistancePx)
        return;

    // Once the OS takes over the drag this button never sees a click for it.
    dragStarted = true;
    setState (buttonNormal);

    const auto file = fileProvider != nullptr ? fileProvider() : juce::File();

    if (file.existsAsFile())
        exporting::DragExport::startFileDrag (file, this);
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
    setLookAndFeel (&lookAndFeel);
    exporting::DragExport::cleanupOldExports();

    auto& apvts = processor.getValueTreeState();
    auto& auth = processor.getAuthManager();

    // Header
    titleLabel.setText ("SnapPlay AI", juce::dontSendNotification);
    titleLabel.setFont (SnapPlayLookAndFeel::font (22.0f, true));
    creditsLabel.setJustificationType (juce::Justification::centredRight);
    creditsLabel.setFont (SnapPlayLookAndFeel::font (14.0f));
    creditsLabel.setColour (juce::Label::textColourId, colours::accent);
    logoutButton.setButtonText ("Log out");
    logoutButton.onClick = [this] { processor.getAuthManager().logout(); };
    addAndMakeVisible (titleLabel);
    addAndMakeVisible (creditsLabel);
    addAndMakeVisible (logoutButton);

    // Input
    dropZone.onBrowse = [this] { openFileChooser(); };
    progressBar.setPercentageDisplay (false);
    progressBar.setStyle (juce::ProgressBar::Style::linear);
    stageLabel.setFont (SnapPlayLookAndFeel::font (13.0f));
    stageLabel.setJustificationType (juce::Justification::centredRight);
    cancelJobButton.setButtonText ("Cancel");
    cancelJobButton.onClick = [this] { processor.getJobClient().cancel(); };
    addAndMakeVisible (dropZone);
    addAndMakeVisible (progressBar);
    addAndMakeVisible (stageLabel);
    addChildComponent (cancelJobButton);

    // Category
    const auto& categoryLabels = SnapPlayAudioProcessor::getCategoryLabels();

    for (int i = 0; i < SnapPlayAudioProcessor::numCategories; ++i)
    {
        auto& button = categoryButtons[static_cast<size_t> (i)];
        button.setButtonText (categoryLabels[i]);
        button.setClickingTogglesState (true);
        button.setRadioGroupId (categoryRadioGroup);
        button.onClick = [this, i]
        {
            if (categoryAttachment != nullptr)
                categoryAttachment->setValueAsCompleteGesture (static_cast<float> (i));
        };
        addAndMakeVisible (button);
    }

    if (auto* categoryParameter = apvts.getParameter (ParamIds::category))
    {
        categoryAttachment = std::make_unique<juce::ParameterAttachment> (*categoryParameter,
                                                                          [this] (float) { updateCategoryButtons(); });
        categoryAttachment->sendInitialUpdate();
    }

    // Scale-Snap
    scaleModeLabel.setText ("Scale-Snap", juce::dontSendNotification);
    scaleModeLabel.setFont (SnapPlayLookAndFeel::font (13.0f));
    scaleModeBox.addItemList ({ "Detected", "Major", "Minor", "Pentatonic Major", "Pentatonic Minor", "Off" }, 1);
    scaleRootLabel.setText ("Root", juce::dontSendNotification);
    scaleRootLabel.setFont (SnapPlayLookAndFeel::font (13.0f));

    for (int pitchClass = 0; pitchClass < 12; ++pitchClass)
        scaleRootBox.addItem (juce::MidiMessage::getMidiNoteName (pitchClass, true, false, middleCOctave), pitchClass + 1);

    detectedKeyLabel.setFont (SnapPlayLookAndFeel::font (14.0f, true));
    bpmLabel.setFont (SnapPlayLookAndFeel::font (14.0f, true));
    addAndMakeVisible (scaleModeLabel);
    addAndMakeVisible (scaleModeBox);
    addAndMakeVisible (scaleRootLabel);
    addAndMakeVisible (scaleRootBox);
    addAndMakeVisible (detectedKeyLabel);
    addAndMakeVisible (bpmLabel);
    scaleModeAttachment = std::make_unique<ComboBoxAttachment> (apvts, ParamIds::scaleMode, scaleModeBox);
    scaleRootAttachment = std::make_unique<ComboBoxAttachment> (apvts, ParamIds::scaleRoot, scaleRootBox);

    // Sound
    setupKnob (attackKnob, attackLabel, "Attack");
    setupKnob (decayKnob, decayLabel, "Decay");
    setupKnob (sustainKnob, sustainLabel, "Sustain");
    setupKnob (releaseKnob, releaseLabel, "Release");
    setupKnob (cutoffKnob, cutoffLabel, "Cutoff");
    setupKnob (resonanceKnob, resonanceLabel, "Resonance");
    setupKnob (gainKnob, gainLabel, "Gain");
    setupKnob (rootTargetKnob, rootTargetLabel, "Root Target");
    attackAttachment     = std::make_unique<SliderAttachment> (apvts, ParamIds::attack, attackKnob);
    decayAttachment      = std::make_unique<SliderAttachment> (apvts, ParamIds::decay, decayKnob);
    sustainAttachment    = std::make_unique<SliderAttachment> (apvts, ParamIds::sustain, sustainKnob);
    releaseAttachment    = std::make_unique<SliderAttachment> (apvts, ParamIds::release, releaseKnob);
    cutoffAttachment     = std::make_unique<SliderAttachment> (apvts, ParamIds::cutoff, cutoffKnob);
    resonanceAttachment  = std::make_unique<SliderAttachment> (apvts, ParamIds::resonance, resonanceKnob);
    gainAttachment       = std::make_unique<SliderAttachment> (apvts, ParamIds::gain, gainKnob);
    rootTargetAttachment = std::make_unique<SliderAttachment> (apvts, ParamIds::rootTarget, rootTargetKnob);
    rootTargetKnob.textFromValueFunction = [] (double value) { return noteNameFor (juce::roundToInt (value)); };
    rootTargetKnob.valueFromTextFunction = [] (const juce::String& text) { return noteNumberFromText (text); };
    rootTargetKnob.updateText();

    drumModeButton.setButtonText ("Drum mode");
    addAndMakeVisible (drumModeButton);
    drumModeAttachment = std::make_unique<ButtonAttachment> (apvts, ParamIds::drumMode, drumModeButton);

    // Export
    dragMidiButton.fileProvider = [this] { return writeExport (true); };
    dragMidiButton.onClick = [this] { openExportSaveDialog (true); };
    dragFscButton.fileProvider = [this] { return writeExport (false); };
    dragFscButton.onClick = [this] { openExportSaveDialog (false); };
    addAndMakeVisible (dragMidiButton);
    addAndMakeVisible (dragFscButton);

    // Keyboard
    keyboard.setAvailableRange (lowestKeyboardNote, highestKeyboardNote);
    keyboard.setOctaveForMiddleC (middleCOctave);
    keyboard.setScrollButtonsVisible (false);
    addAndMakeVisible (keyboard);

    // Overlays
    paywallPrompt.onDismiss = [this]
    {
        paywallDismissed = true;
        showPaywall (false);
    };

    loginOverlay.onLogin = [this] (const juce::String& email, const juce::String& password)
    {
        loginOverlay.setBusy (true);

        juce::Component::SafePointer<SnapPlayAudioProcessorEditor> safeThis (this);
        processor.getAuthManager().login (email, password, [safeThis] (std::optional<cloud::ApiError> error)
        {
            if (safeThis == nullptr)
                return;

            safeThis->loginOverlay.setBusy (false);

            if (error.has_value())
                safeThis->loginOverlay.setErrorMessage (describeError (*error));
            else
                safeThis->loginOverlay.clearForm();
        });
    };

    addChildComponent (paywallPrompt);
    addChildComponent (loginOverlay);

    processor.getJobClient().addChangeListener (this);
    auth.addListener (this);

    setSize (defaultWidth, defaultHeight);

    updateFromProcessor();
    showLoginOverlay (! auth.isLoggedIn());

    if (auth.isLoggedIn())
        auth.refreshBalance();

    startTimer (balanceRefreshIntervalMs);
}

SnapPlayAudioProcessorEditor::~SnapPlayAudioProcessorEditor()
{
    stopTimer();
    fileChooser.reset();

    if (plansRequest != cloud::ApiClient::invalidRequest)
        processor.getApiClient().cancel (plansRequest);

    if (paywallPrompt.isVisible())
        processor.getAuthManager().stopBalancePolling();

    processor.getAuthManager().removeListener (this);
    processor.getJobClient().removeChangeListener (this);

    setLookAndFeel (nullptr);
}

void SnapPlayAudioProcessorEditor::paint (juce::Graphics& g)
{
    g.fillAll (colours::background);
}

void SnapPlayAudioProcessorEditor::resized()
{
    loginOverlay.setBounds (getLocalBounds());
    paywallPrompt.setBounds (getLocalBounds());

    auto bounds = getLocalBounds().reduced (windowMargin, 12);

    auto header = bounds.removeFromTop (headerHeight);
    logoutButton.setBounds (header.removeFromRight (84).reduced (0, 8));
    header.removeFromRight (12);
    creditsLabel.setBounds (header.removeFromRight (140));
    titleLabel.setBounds (header);

    bounds.removeFromTop (8);
    dropZone.setBounds (bounds.removeFromTop (76));
    bounds.removeFromTop (8);

    auto progressRow = bounds.removeFromTop (26);
    cancelJobButton.setBounds (progressRow.removeFromRight (84).reduced (0, 2));
    progressRow.removeFromRight (8);
    stageLabel.setBounds (progressRow.removeFromRight (320));
    progressRow.removeFromRight (8);
    progressBar.setBounds (progressRow.reduced (0, 5));

    bounds.removeFromTop (10);
    auto categoryRow = bounds.removeFromTop (32);

    for (auto& button : categoryButtons)
    {
        button.setBounds (categoryRow.removeFromLeft (120));
        categoryRow.removeFromLeft (8);
    }

    bounds.removeFromTop (10);
    auto scaleRow = bounds.removeFromTop (28);
    scaleModeLabel.setBounds (scaleRow.removeFromLeft (80));
    scaleModeBox.setBounds (scaleRow.removeFromLeft (160));
    scaleRow.removeFromLeft (16);
    scaleRootLabel.setBounds (scaleRow.removeFromLeft (40));
    scaleRootBox.setBounds (scaleRow.removeFromLeft (72));
    scaleRow.removeFromLeft (24);
    detectedKeyLabel.setBounds (scaleRow.removeFromLeft (180));
    bpmLabel.setBounds (scaleRow);

    bounds.removeFromTop (10);
    auto knobRow = bounds.removeFromTop (118);
    juce::Slider* knobs[] = { &attackKnob, &decayKnob, &sustainKnob, &releaseKnob,
                              &cutoffKnob, &resonanceKnob, &gainKnob, &rootTargetKnob };
    juce::Label* knobLabels[] = { &attackLabel, &decayLabel, &sustainLabel, &releaseLabel,
                                  &cutoffLabel, &resonanceLabel, &gainLabel, &rootTargetLabel };

    for (size_t i = 0; i < std::size (knobs); ++i)
    {
        auto cell = knobRow.removeFromLeft (92);
        knobLabels[i]->setBounds (cell.removeFromTop (18));
        knobs[i]->setBounds (cell);
    }

    knobRow.removeFromLeft (8);
    drumModeButton.setBounds (knobRow.removeFromLeft (130).withSizeKeepingCentre (130, 26));

    bounds.removeFromTop (8);
    auto exportRow = bounds.removeFromTop (30);
    dragMidiButton.setBounds (exportRow.removeFromLeft (120));
    exportRow.removeFromLeft (8);
    dragFscButton.setBounds (exportRow.removeFromLeft (120));

    bounds.removeFromTop (10);
    keyboard.setKeyWidth (static_cast<float> (bounds.getWidth()) / static_cast<float> (numWhiteKeys));
    keyboard.setBounds (bounds);
}

//==============================================================================
bool SnapPlayAudioProcessorEditor::isInterestedInFileDrag (const juce::StringArray& files)
{
    if (loginOverlay.isVisible() || processor.getJobClient().isRunning())
        return false;

    for (const auto& path : files)
        if (hasSupportedExtension (path))
            return true;

    return false;
}

void SnapPlayAudioProcessorEditor::fileDragEnter (const juce::StringArray& files, int x, int y)
{
    juce::ignoreUnused (files, x, y);
    dropZone.setHighlighted (true);
}

void SnapPlayAudioProcessorEditor::fileDragExit (const juce::StringArray& files)
{
    juce::ignoreUnused (files);
    dropZone.setHighlighted (false);
}

void SnapPlayAudioProcessorEditor::filesDropped (const juce::StringArray& files, int x, int y)
{
    juce::ignoreUnused (x, y);
    dropZone.setHighlighted (false);

    if (const auto file = firstSupportedFile (files); file.existsAsFile())
        submitAudioFile (file);
}

//==============================================================================
void SnapPlayAudioProcessorEditor::changeListenerCallback (juce::ChangeBroadcaster* source)
{
    auto& job = processor.getJobClient();

    if (source != &job)
        return;

    updateJobStatus();
    updateDetectedKeyAndBpm();

    if (job.getState() == cloud::JobClient::State::Failed)
        if (const auto error = job.getError(); error.has_value() && error->isInsufficientCredits())
        {
            paywallDismissed = false;
            showPaywall (true);
        }
}

void SnapPlayAudioProcessorEditor::authStateChanged (cloud::AuthManager& auth)
{
    const bool loggedIn = auth.isLoggedIn();

    showLoginOverlay (! loggedIn);
    loginOverlay.setBusy (auth.getState() == cloud::AuthManager::State::LoggingIn);
    updateCreditsLabel();

    if (loggedIn)
    {
        if (const auto balance = auth.getBalance(); balance.has_value())
            balanceChanged (auth, *balance);
    }
    else
    {
        paywallDismissed = false;
    }
}

void SnapPlayAudioProcessorEditor::balanceChanged (cloud::AuthManager& auth, const cloud::CreditBalance& balance)
{
    updateCreditsLabel();

    if (! auth.isLoggedIn())
        return;

    if (balance.available <= 0)
    {
        if (! paywallDismissed)
            showPaywall (true);
    }
    else
    {
        paywallDismissed = false;
        showPaywall (false);
    }
}

void SnapPlayAudioProcessorEditor::authError (cloud::AuthManager&, const cloud::ApiError& error)
{
    if (loginOverlay.isVisible())
    {
        loginOverlay.setBusy (false);
        loginOverlay.setErrorMessage (describeError (error));
    }
}

void SnapPlayAudioProcessorEditor::timerCallback()
{
    auto& auth = processor.getAuthManager();

    if (auth.isLoggedIn() && ! auth.isPollingBalance())
        auth.refreshBalance();
}

//==============================================================================
void SnapPlayAudioProcessorEditor::updateFromProcessor()
{
    updateCreditsLabel();
    updateJobStatus();
    updateDetectedKeyAndBpm();
    updateCategoryButtons();
}

void SnapPlayAudioProcessorEditor::updateCreditsLabel()
{
    auto& auth = processor.getAuthManager();

    if (! auth.isLoggedIn())
    {
        creditsLabel.setText ({}, juce::dontSendNotification);
        return;
    }

    const auto balance = auth.getBalance();
    creditsLabel.setText ((balance.has_value() ? juce::String (balance->available) : emDash()) + " credits",
                          juce::dontSendNotification);
}

void SnapPlayAudioProcessorEditor::updateJobStatus()
{
    using State = cloud::JobClient::State;

    const auto& job = processor.getJobClient();
    const auto state = job.getState();
    const auto stageProgress = juce::jlimit (0.0, 1.0, job.getProgress());
    const bool hasResult = processor.getCurrentResult().has_value();

    switch (state)
    {
        case State::Idle:        progressValue = hasResult ? 1.0 : 0.0; break;
        case State::Encoding:    progressValue = 0.05; break;
        case State::Submitting:  progressValue = 0.10; break;
        case State::Queued:      progressValue = 0.15; break;
        case State::Running:     progressValue = 0.20 + 0.65 * stageProgress; break;
        case State::Downloading: progressValue = 0.85 + 0.15 * stageProgress; break;
        case State::Ready:       progressValue = 1.0; break;
        case State::Failed:
        case State::Cancelled:   progressValue = 0.0; break;
    }

    juce::String stageText;
    auto stageColour = colours::textDim;

    if (state == State::Failed)
    {
        const auto error = job.getError();
        stageText = error.has_value() ? describeError (*error) : "Processing failed";
        stageColour = colours::danger;
    }
    else if (state == State::Idle)
    {
        stageText = hasResult ? "Ready" : juce::String();
    }
    else
    {
        stageText = job.getStatusMessage();

        if (state == State::Ready && job.wasInputTruncated())
            stageText += " (input cut to 60 s)";
    }

    stageLabel.setText (stageText, juce::dontSendNotification);
    stageLabel.setColour (juce::Label::textColourId, stageColour);

    const bool running = job.isRunning();
    cancelJobButton.setVisible (running);
    dropZone.setEnabledForDrop (! running);

    if (running)
        dropZone.setMessage ("Processing" + ellipsis() + " " + job.getStatusMessage());
    else if (hasResult)
        dropZone.setMessage ("Loaded job " + processor.getCurrentResult()->jobId.substring (0, 8)
                             + " " + emDash() + " drop another file to replace it");
    else
        dropZone.setMessage (defaultDropMessage());

    const bool exportable = hasExportableResult();
    dragMidiButton.setEnabled (exportable);
    dragFscButton.setEnabled (exportable);
}

void SnapPlayAudioProcessorEditor::updateDetectedKeyAndBpm()
{
    if (const auto key = processor.getDetectedKey(); key.has_value())
        detectedKeyLabel.setText (key->root + " " + key->mode, juce::dontSendNotification);
    else
        detectedKeyLabel.setText (emDash(), juce::dontSendNotification);

    if (const auto bpm = processor.getDetectedBpm(); bpm.has_value())
        bpmLabel.setText (formatBpm (*bpm), juce::dontSendNotification);
    else
        bpmLabel.setText (emDash() + " BPM", juce::dontSendNotification);
}

void SnapPlayAudioProcessorEditor::updateCategoryButtons()
{
    const int selected = processor.getSelectedCategory();

    for (int i = 0; i < SnapPlayAudioProcessor::numCategories; ++i)
        categoryButtons[static_cast<size_t> (i)].setToggleState (i == selected, juce::dontSendNotification);
}

void SnapPlayAudioProcessorEditor::showLoginOverlay (bool show)
{
    if (show)
    {
        showPaywall (false);
        loginOverlay.toFront (false);
    }

    loginOverlay.setVisible (show);
    logoutButton.setVisible (! show);
}

void SnapPlayAudioProcessorEditor::showPaywall (bool show)
{
    auto& auth = processor.getAuthManager();
    auto& api = processor.getApiClient();

    if (show)
    {
        if (! paywallPrompt.isVisible())
        {
            paywallPrompt.setVisible (true);
            paywallPrompt.toFront (false);
            auth.startBalancePolling (paywallPollIntervalMs);
        }

        if (plansRequest == cloud::ApiClient::invalidRequest)
        {
            juce::Component::SafePointer<SnapPlayAudioProcessorEditor> safeThis (this);
            plansRequest = api.getPlans ([safeThis] (cloud::ApiClient::Response<std::vector<cloud::PlanInfo>> response)
            {
                if (safeThis == nullptr)
                    return;

                safeThis->plansRequest = cloud::ApiClient::invalidRequest;

                if (response.ok())
                    safeThis->paywallPrompt.setPlans (*response.value);
            });
        }

        return;
    }

    if (paywallPrompt.isVisible())
    {
        paywallPrompt.setVisible (false);
        auth.stopBalancePolling();
    }

    if (plansRequest != cloud::ApiClient::invalidRequest)
    {
        api.cancel (plansRequest);
        plansRequest = cloud::ApiClient::invalidRequest;
    }
}

void SnapPlayAudioProcessorEditor::openFileChooser()
{
    if (processor.getJobClient().isRunning())
        return;

    fileChooser = std::make_unique<juce::FileChooser> ("Choose an audio file",
                                                       juce::File::getSpecialLocation (juce::File::userMusicDirectory),
                                                       cloud::UploadEncoder::getSupportedWildcards());

    juce::Component::SafePointer<SnapPlayAudioProcessorEditor> safeThis (this);
    fileChooser->launchAsync (juce::FileBrowserComponent::openMode | juce::FileBrowserComponent::canSelectFiles,
                              [safeThis] (const juce::FileChooser& chooser)
                              {
                                  if (safeThis == nullptr)
                                      return;

                                  if (const auto file = chooser.getResult(); file.existsAsFile())
                                      safeThis->submitAudioFile (file);
                              });
}

void SnapPlayAudioProcessorEditor::setupKnob (juce::Slider& slider, juce::Label& label, const juce::String& text)
{
    slider.setSliderStyle (juce::Slider::RotaryHorizontalVerticalDrag);
    slider.setTextBoxStyle (juce::Slider::TextBoxBelow, false, 76, 18);
    slider.setRotaryParameters (juce::MathConstants<float>::pi * 1.25f, juce::MathConstants<float>::pi * 2.75f, true);

    label.setText (text, juce::dontSendNotification);
    label.setJustificationType (juce::Justification::centred);
    label.setFont (SnapPlayLookAndFeel::font (13.0f));
    label.setColour (juce::Label::textColourId, colours::textDim);

    addAndMakeVisible (slider);
    addAndMakeVisible (label);
}

//==============================================================================
void SnapPlayAudioProcessorEditor::submitAudioFile (const juce::File& file)
{
    auto& auth = processor.getAuthManager();

    if (auth.getBalance().has_value() && auth.getAvailableCredits() <= 0)
    {
        paywallDismissed = false;
        showPaywall (true);
        return;
    }

    processor.submitAudioFile (file);
}

bool SnapPlayAudioProcessorEditor::hasExportableResult() const
{
    const auto& result = processor.getCurrentResult();
    return result.has_value() && ! result->midi.tracks.empty();
}

juce::File SnapPlayAudioProcessorEditor::writeExport (bool midi)
{
    const auto& result = processor.getCurrentResult();

    if (! result.has_value())
        return {};

    const auto baseName = exporting::MidiExporter::suggestedBaseName (*result);

    return midi ? exporting::MidiExporter::writeExportFile (*result, baseName)
                : exporting::FscExporter::writeExportFile (*result, baseName);
}

void SnapPlayAudioProcessorEditor::openExportSaveDialog (bool midi)
{
    const auto& result = processor.getCurrentResult();

    if (! result.has_value())
        return;

    const juce::String extension = midi ? exporting::MidiExporter::extension : exporting::FscExporter::extension;
    const auto initialFile = juce::File::getSpecialLocation (juce::File::userDocumentsDirectory)
                                 .getChildFile (exporting::MidiExporter::suggestedBaseName (*result) + extension);

    fileChooser = std::make_unique<juce::FileChooser> (midi ? "Save MIDI file" : "Save FL Studio score",
                                                       initialFile, "*" + extension);

    juce::Component::SafePointer<SnapPlayAudioProcessorEditor> safeThis (this);
    fileChooser->launchAsync (juce::FileBrowserComponent::saveMode | juce::FileBrowserComponent::canSelectFiles
                                  | juce::FileBrowserComponent::warnAboutOverwriting,
                              [safeThis, midi, extension] (const juce::FileChooser& chooser)
                              {
                                  if (safeThis == nullptr)
                                      return;

                                  const auto& currentResult = safeThis->processor.getCurrentResult();
                                  const auto chosen = chooser.getResult();

                                  if (chosen == juce::File() || ! currentResult.has_value())
                                      return;

                                  const auto target = chosen.withFileExtension (extension);
                                  const auto& tracks = currentResult->midi.tracks;
                                  const auto bpm = currentResult->analysis.bpm;
                                  const bool written = midi ? exporting::MidiExporter::writeToFile (tracks, bpm, target)
                                                            : exporting::FscExporter::writeToFile (tracks, bpm, target);

                                  safeThis->stageLabel.setText ((written ? "Saved " : "Could not write ") + target.getFileName(),
                                                                juce::dontSendNotification);
                                  safeThis->stageLabel.setColour (juce::Label::textColourId,
                                                                  written ? colours::textDim : colours::danger);
                              });
}

} // namespace snapplay
