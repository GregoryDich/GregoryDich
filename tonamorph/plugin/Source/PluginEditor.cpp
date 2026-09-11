#include "PluginEditor.h"

#include "Cloud/UploadEncoder.h"
#include "Core/Retention.h"
#include "Core/SemanticVersion.h"
#include "Core/Strings.h"
#include "DemoData.h"
#include "Export/DragExport.h"
#include "Export/FscExporter.h"
#include "Export/MidiExporter.h"

#include <iterator>
#include <utility>

namespace tonamorph
{

namespace colours = ui::colours;
using ui::TonamorphLookAndFeel;

namespace
{
    constexpr int windowMargin = 16;
    constexpr int headerHeight = 44;
    constexpr int dragStartDistancePx = 8;
    constexpr int uiTickMs = 250;
    constexpr int balanceRefreshTicks = 60'000 / uiTickMs;
    constexpr int paywallPollIntervalMs = 5000;
    constexpr int lowestKeyboardNote = 24;
    constexpr int highestKeyboardNote = 108;
    constexpr int numWhiteKeys = 50;   ///< white keys between lowestKeyboardNote and highestKeyboardNote
    constexpr int categoryRadioGroup = 1001;
    constexpr int middleCOctave = 4;              ///< MIDI 60 = C4, so the contract's default root 48 reads C3
    constexpr int firstSoundNote = 48;             ///< C3
    constexpr int celebrationGlowMs = 2000;
    constexpr int celebrationToastMs = 3500;
    constexpr double shakyKeyConfidence = 0.6;    ///< GTM B §1 criterion 4
    constexpr int versionCheckHours = 24;

    juce::String s (const char* text) { return juce::String::fromUTF8 (text); }

    juce::String fill (const char* text, const char* placeholder, const juce::String& value)
    {
        return juce::String::fromUTF8 (strings::fill (text, placeholder, value.toStdString()).c_str());
    }

    /** The website the account pages live on: the COMPANY_WEBSITE the plugin is built with. */
    juce::String siteUrl()
    {
        return juce::String (JucePlugin_ManufacturerWebsite).trimCharactersAtEnd ("/");
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

    /** "9" or "7.99": the digits that go after the "$" in the paywall templates. */
    juce::String priceDigits (double usd)
    {
        const auto cents = juce::roundToInt (usd * 100.0);
        return cents % 100 == 0 ? juce::String (cents / 100) : juce::String (usd, 2);
    }

    juce::String formatBpm (double bpm)
    {
        const auto tenths = juce::roundToInt (bpm * 10.0);
        return tenths % 10 == 0 ? juce::String (tenths / 10) : juce::String (bpm, 1);
    }

    juce::String describeKey (const cloud::KeyInfo& key)
    {
        return key.root + " " + key.mode;
    }

    enum class ErrorContext { Login, Job };

    /** Maps a contract §5 error (or a client-side one) to the GTM B §3 copy. */
    juce::String userMessageFor (const cloud::ApiError& error, ErrorContext context)
    {
        const auto& code = error.code;
        const int status = error.httpStatus;

        if (code == "cancelled")
            return s (strings::cancelled);

        if (code == "network_error")
            return s (strings::errorOffline);

        if (context == ErrorContext::Login)
        {
            if (status == 429 || code == "rate_limited")
                return s (strings::errorAuthRateLimited);

            if (status == 401 || code == "unauthorized")
                return error.message.containsIgnoreCase ("confirm") ? s (strings::errorUnconfirmedEmail)
                                                                     : s (strings::errorWrongPassword);

            return s (strings::errorGeneric);
        }

        if (status == 413 || code == "payload_too_large")                          return s (strings::errorTooLarge);
        if (status == 415 || code == "unsupported_media_type" || code == "encode_failed") return s (strings::errorUnsupported);
        if (status == 429 || code == "rate_limited")                               return s (strings::errorRateLimited);
        if (code == "service_unavailable")                                         return s (strings::errorMaintenance);
        if (status == 503 || code == "worker_unavailable")                         return s (strings::errorWorkerBusy);
        if (code == "insufficient_credits")                                        return s (strings::errorNoCredits);
        if (status == 401 || code == "unauthorized" || code == "token_expired")    return s (strings::errorSignInAgain);
        if (code == "cache_missing" || code == "expired")                          return s (strings::errorCacheMissing);
        if (code == "lost_contact")                                                return s (strings::errorLostContact);

        return s (strings::errorMorphFailed);
    }

} // namespace

//==============================================================================
PaywallPrompt::PaywallPrompt()
{
    headlineLabel.setText (s (strings::paywallHeadline), juce::dontSendNotification);
    headlineLabel.setJustificationType (juce::Justification::centred);
    headlineLabel.setFont (TonamorphLookAndFeel::font (19.0f, true));
    headlineLabel.setMinimumHorizontalScale (1.0f);

    for (auto* line : { &packLine, &subscriptionLine })
    {
        line->setJustificationType (juce::Justification::centred);
        line->setFont (TonamorphLookAndFeel::font (12.5f));
        line->setColour (juce::Label::textColourId, colours::textDim);
    }

    dismissButton.setButtonText (s (strings::notNow));

    onCheckout = [] (const cloud::PlanInfo* plan)
    {
        const auto url = plan != nullptr && plan->checkoutUrl.has_value() && plan->checkoutUrl->isNotEmpty()
                             ? *plan->checkoutUrl
                             : siteUrl();
        juce::URL (url).launchInDefaultBrowser();
    };

    buyPackButton.onClick = [this]
    {
        if (onCheckout != nullptr)
            onCheckout (findPlan (false));
    };

    subscribeButton.onClick = [this]
    {
        if (onCheckout != nullptr)
            onCheckout (findPlan (true));
    };

    dismissButton.onClick = [this]
    {
        if (onDismiss != nullptr)
            onDismiss();
    };

    addAndMakeVisible (headlineLabel);
    addAndMakeVisible (buyPackButton);
    addAndMakeVisible (packLine);
    addAndMakeVisible (subscribeButton);
    addAndMakeVisible (subscriptionLine);
    addAndMakeVisible (dismissButton);

    rebuild();
}

void PaywallPrompt::setPlans (const std::vector<cloud::PlanInfo>& newPlans)
{
    plans = newPlans;
    rebuild();
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
    auto area = getPanelBounds().reduced (28, 22);
    constexpr int buttonHeight = 38;   // all three buttons: same width, same height

    headlineLabel.setBounds (area.removeFromTop (56));
    area.removeFromTop (14);
    buyPackButton.setBounds (area.removeFromTop (buttonHeight));
    packLine.setBounds (area.removeFromTop (20));
    area.removeFromTop (8);
    subscribeButton.setBounds (area.removeFromTop (buttonHeight));
    subscriptionLine.setBounds (area.removeFromTop (20));
    area.removeFromTop (8);
    dismissButton.setBounds (area.removeFromTop (buttonHeight));
}

void PaywallPrompt::rebuild()
{
    const auto* pack = findPlan (false);
    const auto* subscription = findPlan (true);

    const auto packCredits = juce::String (pack != nullptr ? pack->credits : strings::paywallDefaultPackCredits);
    const auto packPrice = pack != nullptr ? priceDigits (pack->priceUsd) : s (strings::paywallDefaultPackPrice);
    const auto subCredits = juce::String (subscription != nullptr ? subscription->credits : strings::paywallDefaultSubCredits);
    const auto subPrice = subscription != nullptr ? priceDigits (subscription->priceUsd) : s (strings::paywallDefaultSubPrice);

    buyPackButton.setButtonText (fill (strings::fill (strings::paywallPackButton, "count", packCredits.toStdString()).c_str(),
                                       "price", packPrice));
    subscribeButton.setButtonText (fill (strings::fill (strings::paywallSubscribeButton, "count", subCredits.toStdString()).c_str(),
                                         "price", subPrice));
    packLine.setText (s (strings::paywallPackLine), juce::dontSendNotification);
    subscriptionLine.setText (fill (strings::paywallSubscriptionLine, "count", subCredits), juce::dontSendNotification);
    resized();
}

const cloud::PlanInfo* PaywallPrompt::findPlan (bool subscription) const
{
    for (const auto& plan : plans)
        if (plan.isSubscription() == subscription && plan.credits > 0 && plan.priceUsd > 0.0)
            return &plan;

    return nullptr;
}

juce::Rectangle<int> PaywallPrompt::getPanelBounds() const
{
    return getLocalBounds().withSizeKeepingCentre (juce::jmin (480, getWidth() - 32), 324);
}

//==============================================================================
LoginOverlay::LoginOverlay()
    : signupLink (s (strings::createAccount), juce::URL (siteUrl() + "/signup")),
      forgotPasswordLink (s (strings::forgotPassword), juce::URL (siteUrl() + "/reset-password"))
{
    titleLabel.setText (fill (strings::signInTitle, "product", strings::productName), juce::dontSendNotification);
    titleLabel.setJustificationType (juce::Justification::centred);
    titleLabel.setFont (TonamorphLookAndFeel::font (22.0f, true));

    messageLabel.setJustificationType (juce::Justification::centred);
    messageLabel.setFont (TonamorphLookAndFeel::font (14.0f));
    messageLabel.setColour (juce::Label::textColourId, colours::accent);

    emailLabel.setText (s (strings::email), juce::dontSendNotification);
    emailLabel.setFont (TonamorphLookAndFeel::font (13.0f));
    emailEditor.setTextToShowWhenEmpty (s (strings::emailPlaceholder), colours::textDim);
    emailEditor.setFont (TonamorphLookAndFeel::font (15.0f));
    emailEditor.onReturnKey = [this] { passwordEditor.grabKeyboardFocus(); };

    passwordLabel.setText (s (strings::password), juce::dontSendNotification);
    passwordLabel.setFont (TonamorphLookAndFeel::font (13.0f));
    passwordEditor.setPasswordCharacter (0x2022);
    passwordEditor.setFont (TonamorphLookAndFeel::font (15.0f));
    passwordEditor.onReturnKey = [this] { submit(); };

    loginButton.setButtonText (s (strings::signIn));
    loginButton.onClick = [this] { submit(); };

    statusLabel.setJustificationType (juce::Justification::centred);
    statusLabel.setFont (TonamorphLookAndFeel::font (13.0f));
    statusLabel.setColour (juce::Label::textColourId, colours::danger);

    signupLink.setJustificationType (juce::Justification::centred);
    signupLink.setFont (TonamorphLookAndFeel::font (13.0f), false);
    forgotPasswordLink.setJustificationType (juce::Justification::centred);
    forgotPasswordLink.setFont (TonamorphLookAndFeel::font (13.0f), false);

    dismissButton.setButtonText (s (strings::notNow));
    dismissButton.onClick = [this]
    {
        if (onDismiss != nullptr)
            onDismiss();
    };

    addAndMakeVisible (titleLabel);
    addAndMakeVisible (messageLabel);
    addAndMakeVisible (emailLabel);
    addAndMakeVisible (emailEditor);
    addAndMakeVisible (passwordLabel);
    addAndMakeVisible (passwordEditor);
    addAndMakeVisible (loginButton);
    addAndMakeVisible (statusLabel);
    addAndMakeVisible (signupLink);
    addAndMakeVisible (forgotPasswordLink);
    addAndMakeVisible (dismissButton);
}

void LoginOverlay::setBusy (bool busy)
{
    emailEditor.setEnabled (! busy);
    passwordEditor.setEnabled (! busy);
    loginButton.setEnabled (! busy);
    loginButton.setButtonText (busy ? s (strings::signingIn) : s (strings::signIn));
}

void LoginOverlay::setErrorMessage (const juce::String& message)
{
    statusLabel.setText (message, juce::dontSendNotification);
}

void LoginOverlay::setMessage (const juce::String& message)
{
    messageLabel.setText (message, juce::dontSendNotification);
}

void LoginOverlay::clearForm()
{
    emailEditor.clear();
    passwordEditor.clear();
    statusLabel.setText ({}, juce::dontSendNotification);
}

void LoginOverlay::paint (juce::Graphics& g)
{
    g.fillAll (colours::background.withAlpha (0.94f));

    const auto panel = getPanelBounds().toFloat();
    g.setColour (colours::panel);
    g.fillRoundedRectangle (panel, 10.0f);
    g.setColour (colours::outline);
    g.drawRoundedRectangle (panel, 10.0f, 1.0f);
}

void LoginOverlay::resized()
{
    auto area = getPanelBounds().reduced (28, 22);

    titleLabel.setBounds (area.removeFromTop (32));
    messageLabel.setBounds (area.removeFromTop (22));
    area.removeFromTop (10);

    emailLabel.setBounds (area.removeFromTop (18));
    emailEditor.setBounds (area.removeFromTop (30));
    area.removeFromTop (10);

    passwordLabel.setBounds (area.removeFromTop (18));
    passwordEditor.setBounds (area.removeFromTop (30));
    area.removeFromTop (16);

    loginButton.setBounds (area.removeFromTop (34));
    area.removeFromTop (6);
    statusLabel.setBounds (area.removeFromTop (32));

    auto links = area.removeFromTop (22);
    signupLink.setBounds (links.removeFromLeft (links.getWidth() / 2));
    forgotPasswordLink.setBounds (links);
    area.removeFromTop (10);
    dismissButton.setBounds (area.removeFromTop (30).withSizeKeepingCentre (120, 30));
}

void LoginOverlay::submit()
{
    const auto email = emailEditor.getText().trim();
    const auto password = passwordEditor.getText();

    if (email.isEmpty() || ! email.containsChar ('@') || password.isEmpty())
    {
        setErrorMessage (s (strings::enterCredentials));
        return;
    }

    setErrorMessage ({});

    if (onLogin != nullptr)
        onLogin (email, password);
}

juce::Rectangle<int> LoginOverlay::getPanelBounds() const
{
    return getLocalBounds().withSizeKeepingCentre (juce::jmin (380, getWidth() - 32), 404);
}

//==============================================================================
DropZone::DropZone()
{
    messageLabel.setJustificationType (juce::Justification::centred);
    messageLabel.setFont (TonamorphLookAndFeel::font (15.0f));
    messageLabel.setInterceptsMouseClicks (false, false);
    setMouseCursor (juce::MouseCursor::PointingHandCursor);
    setMessage (s (strings::dropZone));
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

void ExportDragButton::pulse()
{
    setColour (juce::TextButton::buttonColourId, colours::accentDim);
    repaint();

    juce::Component::SafePointer<ExportDragButton> safeThis (this);
    juce::Timer::callAfterDelay (900, [safeThis]
    {
        if (safeThis != nullptr)
        {
            safeThis->removeColour (juce::TextButton::buttonColourId);
            safeThis->repaint();
        }
    });
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

    if (! file.existsAsFile())
        return;

    juce::Component::SafePointer<ExportDragButton> safeThis (this);
    exporting::DragExport::startFileDrag (file, this, [safeThis]
    {
        if (safeThis == nullptr || safeThis->onDragFinished == nullptr)
            return;

        // "Landed" means the pointer let go somewhere other than this window: the DAW.
        const auto pointer = juce::Desktop::getInstance().getMainMouseSource().getScreenPosition().toInt();
        auto* window = safeThis->getTopLevelComponent();
        const bool landedOutside = window == nullptr || ! window->getScreenBounds().contains (pointer);
        safeThis->onDragFinished (landedOutside);
    });
}

void ExportDragButton::mouseUp (const juce::MouseEvent& event)
{
    juce::TextButton::mouseUp (event);
    dragStarted = false;
}

//==============================================================================
TonamorphAudioProcessorEditor::TonamorphAudioProcessorEditor (TonamorphAudioProcessor& processorToUse)
    : juce::AudioProcessorEditor (processorToUse),
      processor (processorToUse),
      progressBar (progressValue),
      dragMidiButton (s (strings::dragMid)),
      dragFscButton (s (strings::dragFsc)),
      keyboard (processorToUse.getKeyboardState(), juce::MidiKeyboardComponent::horizontalKeyboard)
{
    setLookAndFeel (&lookAndFeel);
    exporting::DragExport::cleanupOldExports();

    auto& apvts = processor.getValueTreeState();
    auto& auth = processor.getAuthManager();

    // Banner + header
    versionBanner.onDismiss = [this]
    {
        if (const auto info = processor.getSettings().getCachedVersionInfo(); info.has_value())
            processor.getSettings().setDismissedUpdateVersion (info->latest);

        versionBanner.hide();
        resized();
    };
    addChildComponent (versionBanner);

    titleLabel.setText (s (strings::productName), juce::dontSendNotification);
    titleLabel.setFont (TonamorphLookAndFeel::font (22.0f, true));
    settingsButton.setButtonText (s (strings::settings));
    settingsButton.onClick = [this] { openSettingsMenu(); };
    aboutButton.setButtonText (s (strings::about));
    aboutButton.onClick = [this] { showAbout (true); };
    referralButton.setButtonText (s (strings::referralShare));
    referralButton.setColour (juce::TextButton::textColourOffId, colours::accent);
    referralButton.onClick = [this] { showReferral (true); };
    creditsLabel.setJustificationType (juce::Justification::centredRight);
    creditsLabel.setFont (TonamorphLookAndFeel::font (14.0f));
    creditsLabel.setColour (juce::Label::textColourId, colours::accent);
    signInButton.setButtonText (s (strings::signIn));
    signInButton.onClick = [this]
    {
        loginOverlay.setMessage ({});
        showLoginOverlay (true);
    };
    logoutButton.setButtonText (s (strings::logOut));
    logoutButton.onClick = [this] { processor.getAuthManager().logout(); };
    addAndMakeVisible (titleLabel);
    addAndMakeVisible (settingsButton);
    addAndMakeVisible (aboutButton);
    addChildComponent (referralButton);
    addAndMakeVisible (creditsLabel);
    addAndMakeVisible (signInButton);
    addAndMakeVisible (logoutButton);

    // Input
    dropZone.onBrowse = [this] { openFileChooser(); };
    progressBar.setPercentageDisplay (false);
    progressBar.setStyle (juce::ProgressBar::Style::linear);
    stageLabel.setFont (TonamorphLookAndFeel::font (13.0f));
    stageLabel.setJustificationType (juce::Justification::centredRight);
    cancelJobButton.setButtonText (s (strings::cancel));
    cancelJobButton.onClick = [this] { processor.getJobClient().cancel(); };
    addAndMakeVisible (dropZone);
    addAndMakeVisible (progressBar);
    addAndMakeVisible (stageLabel);
    addChildComponent (cancelJobButton);

    // Category
    const auto& categoryLabels = TonamorphAudioProcessor::getCategoryLabels();

    for (int i = 0; i < TonamorphAudioProcessor::numCategories; ++i)
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
    scaleModeLabel.setText (s (strings::scaleSnap), juce::dontSendNotification);
    scaleModeLabel.setFont (TonamorphLookAndFeel::font (13.0f));
    scaleModeBox.addItemList ({ "Detected", "Major", "Minor", "Pentatonic Major", "Pentatonic Minor", "Off" }, 1);
    scaleRootLabel.setText (s (strings::scaleRoot), juce::dontSendNotification);
    scaleRootLabel.setFont (TonamorphLookAndFeel::font (13.0f));

    for (int pitchClass = 0; pitchClass < 12; ++pitchClass)
        scaleRootBox.addItem (juce::MidiMessage::getMidiNoteName (pitchClass, true, false, middleCOctave), pitchClass + 1);

    detectedKeyLabel.setFont (TonamorphLookAndFeel::font (14.0f, true));
    shakyKeyButton.setButtonText (s (strings::shakyKey));
    shakyKeyButton.setColour (juce::TextButton::textColourOffId, colours::accent);
    shakyKeyButton.onClick = [this] { scaleRootBox.showPopup(); };
    bpmLabel.setFont (TonamorphLookAndFeel::font (14.0f, true));
    addAndMakeVisible (scaleModeLabel);
    addAndMakeVisible (scaleModeBox);
    addAndMakeVisible (scaleRootLabel);
    addAndMakeVisible (scaleRootBox);
    addAndMakeVisible (detectedKeyLabel);
    addChildComponent (shakyKeyButton);
    addAndMakeVisible (bpmLabel);
    scaleModeAttachment = std::make_unique<ComboBoxAttachment> (apvts, ParamIds::scaleMode, scaleModeBox);
    scaleRootAttachment = std::make_unique<ComboBoxAttachment> (apvts, ParamIds::scaleRoot, scaleRootBox);

    // Sound: knob captions are the host-visible parameter names.
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

    drumModeButton.setButtonText (s (strings::drumMode));
    addAndMakeVisible (drumModeButton);
    drumModeAttachment = std::make_unique<ButtonAttachment> (apvts, ParamIds::drumMode, drumModeButton);

    // Export + feedback
    dragMidiButton.fileProvider = [this] { return writeExport (true); };
    dragMidiButton.onClick = [this] { openExportSaveDialog (true); };
    dragMidiButton.onDragFinished = [this] (bool landed) { onExportDragFinished (true, landed); };
    dragFscButton.fileProvider = [this] { return writeExport (false); };
    dragFscButton.onClick = [this] { openExportSaveDialog (false); };
    dragFscButton.onDragFinished = [this] (bool landed) { onExportDragFinished (false, landed); };
    addAndMakeVisible (dragMidiButton);
    addAndMakeVisible (dragFscButton);

    feedbackBar.onSubmit = [this] (bool thumbsUp, const juce::String& reason, const juce::String& note)
    {
        feedbackBar.setBusy (true);

        juce::Component::SafePointer<TonamorphAudioProcessorEditor> safeThis (this);
        processor.submitFeedback (thumbsUp, reason, note, [safeThis] (TonamorphAudioProcessor::FeedbackOutcome outcome)
        {
            if (safeThis == nullptr)
                return;

            using Outcome = TonamorphAudioProcessor::FeedbackOutcome;

            switch (outcome)
            {
                case Outcome::Sent:     safeThis->feedbackBar.showOutcome (s (strings::feedbackThanks), false); break;
                case Outcome::Refunded: safeThis->feedbackBar.showOutcome (s (strings::feedbackRefunded), false); break;
                case Outcome::Failed:   safeThis->feedbackBar.showOutcome (s (strings::feedbackFailed), true); break;
            }
        });
    };
    addChildComponent (feedbackBar);

    // Keyboard + toast
    keyboard.setAvailableRange (lowestKeyboardNote, highestKeyboardNote);
    keyboard.setOctaveForMiddleC (middleCOctave);
    keyboard.setScrollButtonsVisible (false);
    addAndMakeVisible (keyboard);
    addChildComponent (toast);

    // Overlays
    paywallPrompt.onDismiss = [this]
    {
        paywallDismissed = true;
        showPaywall (false);
    };

    loginOverlay.onDismiss = [this]
    {
        pendingDropFile = juce::File();
        showLoginOverlay (false);
    };

    loginOverlay.onLogin = [this] (const juce::String& email, const juce::String& password)
    {
        loginOverlay.setBusy (true);

        juce::Component::SafePointer<TonamorphAudioProcessorEditor> safeThis (this);
        processor.getAuthManager().login (email, password, [safeThis] (std::optional<cloud::ApiError> error)
        {
            if (safeThis == nullptr)
                return;

            safeThis->loginOverlay.setBusy (false);

            if (error.has_value())
                safeThis->loginOverlay.setErrorMessage (userMessageFor (*error, ErrorContext::Login));
            else
                safeThis->loginOverlay.clearForm();
        });
    };

    addChildComponent (paywallPrompt);
    addChildComponent (loginOverlay);

    aboutOverlay.setNoticesText (juce::String::fromUTF8 (DemoData::third_party_notices_txt,
                                                         DemoData::third_party_notices_txtSize));
    aboutOverlay.onCrashReportingChanged = [this] (bool enabled) { processor.setCrashReportingEnabled (enabled); };
    aboutOverlay.onClose = [this] { showAbout (false); };
    referralPanel.onClose = [this] { showReferral (false); };
    npsCard.onSubmit = [this] (int score, const juce::String& comment) { submitNps (score, comment); };
    npsCard.onDismiss = [this]
    {
        processor.getSettings().incrementNpsDismissals();
        npsCard.hideCard();
    };
    addChildComponent (aboutOverlay);
    addChildComponent (referralPanel);
    addChildComponent (npsCard);

    processor.getJobClient().addChangeListener (this);
    processor.getResultEvents().addChangeListener (this);
    auth.addListener (this);

    setSize (defaultWidth, defaultHeight);

    processor.flushCrashReports();
    processor.loadDemoIfIdle();
    updateFromProcessor();
    updateReferralButton();
    checkForUpdates();

    if (auth.isLoggedIn())
    {
        if (const auto balance = auth.getBalance(); balance.has_value())
        {
            lastKnownAvailable = balance->available;
            lastKnownCredits = balance->credits;
        }

        auth.refreshBalance();
    }

    maybeShowNpsCard();
    startTimer (uiTickMs);
}

TonamorphAudioProcessorEditor::~TonamorphAudioProcessorEditor()
{
    stopTimer();
    fileChooser.reset();

    auto& api = processor.getApiClient();

    if (plansRequest != cloud::ApiClient::invalidRequest)
        api.cancel (plansRequest);

    if (versionRequest != cloud::ApiClient::invalidRequest)
        api.cancel (versionRequest);

    if (npsRequest != cloud::ApiClient::invalidRequest)
        api.cancel (npsRequest);

    if (paywallPrompt.isVisible())
        processor.getAuthManager().stopBalancePolling();

    processor.getAuthManager().removeListener (this);
    processor.getResultEvents().removeChangeListener (this);
    processor.getJobClient().removeChangeListener (this);

    setLookAndFeel (nullptr);
}

void TonamorphAudioProcessorEditor::paint (juce::Graphics& g)
{
    g.fillAll (colours::background);
}

void TonamorphAudioProcessorEditor::resized()
{
    loginOverlay.setBounds (getLocalBounds());
    paywallPrompt.setBounds (getLocalBounds());
    aboutOverlay.setBounds (getLocalBounds());
    referralPanel.setBounds (getLocalBounds());

    auto bounds = getLocalBounds().reduced (windowMargin, 12);

    if (versionBanner.isVisible())
    {
        versionBanner.setBounds (bounds.removeFromTop (ui::VersionBanner::preferredHeight));
        bounds.removeFromTop (8);
    }

    auto header = bounds.removeFromTop (headerHeight);
    auto sessionButtonArea = header.removeFromRight (84).reduced (0, 8);
    signInButton.setBounds (sessionButtonArea);
    logoutButton.setBounds (sessionButtonArea);
    header.removeFromRight (12);
    creditsLabel.setBounds (header.removeFromRight (140));
    header.removeFromRight (12);
    settingsButton.setBounds (header.removeFromRight (90).reduced (0, 8));
    header.removeFromRight (8);
    aboutButton.setBounds (header.removeFromRight (70).reduced (0, 8));

    if (referralButton.isVisible())
    {
        header.removeFromRight (8);
        referralButton.setBounds (header.removeFromRight (190).reduced (0, 8));
    }

    titleLabel.setBounds (header);

    bounds.removeFromTop (8);
    dropZone.setBounds (bounds.removeFromTop (76));
    bounds.removeFromTop (8);

    auto progressRow = bounds.removeFromTop (26);
    cancelJobButton.setBounds (progressRow.removeFromRight (84).reduced (0, 2));
    progressRow.removeFromRight (8);
    stageLabel.setBounds (progressRow.removeFromRight (400));
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
    detectedKeyLabel.setBounds (scaleRow.removeFromLeft (110));
    bpmLabel.setBounds (scaleRow.removeFromRight (100));
    shakyKeyButton.setBounds (scaleRow.reduced (8, 0));

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
    exportRow.removeFromLeft (16);
    feedbackBar.setBounds (exportRow);

    bounds.removeFromTop (10);
    keyboard.setKeyWidth (static_cast<float> (bounds.getWidth()) / static_cast<float> (numWhiteKeys));
    keyboard.setBounds (bounds);
    npsCard.setBounds (bounds.removeFromBottom (juce::jmin (ui::NpsCard::preferredHeight, bounds.getHeight())));
    placeToast();
}

void TonamorphAudioProcessorEditor::placeToast()
{
    const auto area = keyboard.getBounds();
    toast.setBounds (juce::Rectangle<int> (juce::jmin (620, area.getWidth() - 40), 32)
                         .withCentre ({ area.getCentreX(), area.getY() + 26 }));
    toast.toFront (false);
}

//==============================================================================
bool TonamorphAudioProcessorEditor::isInterestedInFileDrag (const juce::StringArray& files)
{
    if (processor.getJobClient().isRunning())
        return false;

    for (const auto& path : files)
        if (hasSupportedExtension (path))
            return true;

    return false;
}

void TonamorphAudioProcessorEditor::fileDragEnter (const juce::StringArray& files, int x, int y)
{
    juce::ignoreUnused (files, x, y);
    dropZone.setHighlighted (true);
}

void TonamorphAudioProcessorEditor::fileDragExit (const juce::StringArray& files)
{
    juce::ignoreUnused (files);
    dropZone.setHighlighted (false);
}

void TonamorphAudioProcessorEditor::filesDropped (const juce::StringArray& files, int x, int y)
{
    juce::ignoreUnused (x, y);
    dropZone.setHighlighted (false);

    if (const auto file = firstSupportedFile (files); file.existsAsFile())
        submitAudioFile (file);
}

//==============================================================================
void TonamorphAudioProcessorEditor::changeListenerCallback (juce::ChangeBroadcaster* source)
{
    if (source == &processor.getResultEvents())
    {
        onResultEvent();
        return;
    }

    auto& job = processor.getJobClient();

    if (source != &job)
        return;

    updateJobStatus();
    updateDetectedKeyAndBpm();
    updateFeedbackBar();

    if (job.getState() == cloud::JobClient::State::Failed)
        if (const auto error = job.getError(); error.has_value() && error->isInsufficientCredits())
        {
            paywallDismissed = false;
            showPaywall (true);
        }
}

void TonamorphAudioProcessorEditor::authStateChanged (cloud::AuthManager& auth)
{
    const bool loggedIn = auth.isLoggedIn();

    signInButton.setVisible (! loggedIn);
    logoutButton.setVisible (loggedIn);
    loginOverlay.setBusy (auth.getState() == cloud::AuthManager::State::LoggingIn);
    updateCreditsLabel();
    updateJobStatus();

    updateReferralButton();

    if (loggedIn)
    {
        showLoginOverlay (false);

        if (const auto balance = auth.getBalance(); balance.has_value())
            balanceChanged (auth, *balance);

        if (const auto file = std::exchange (pendingDropFile, juce::File()); file.existsAsFile())
            submitAudioFile (file);

        maybeShowNpsCard();
    }
    else
    {
        paywallDismissed = false;
        lastKnownAvailable.reset();
        lastKnownCredits.reset();
        showPaywall (false);
        npsCard.hideCard();   // an answer needs a session; not counted as a dismissal
    }
}

void TonamorphAudioProcessorEditor::balanceChanged (cloud::AuthManager& auth, const cloud::CreditBalance& balance)
{
    updateCreditsLabel();

    if (! auth.isLoggedIn())
        return;

    auto& settings = processor.getSettings();

    // Week-one gift (GTM §2.4) before the purchase check: +2 on an empty balance is the
    // gift, not a purchase.
    if (! settings.hasSeen (PluginSettings::flagWeekOneGift) && weekOneGiftArrived (balance))
    {
        settings.markSeen (PluginSettings::flagWeekOneGift);
        toast.show (s (strings::giftWeekOne), celebrationToastMs + 1500);
    }
    // First purchase (GTM §2.4): the balance poll sees 0 turn into a positive number.
    else if (lastKnownAvailable.has_value() && *lastKnownAvailable <= 0 && balance.available > 0
             && ! settings.hasSeen (PluginSettings::flagFirstPurchase))
    {
        settings.markSeen (PluginSettings::flagFirstPurchase);
        toast.show (fill (strings::celebrateFirstPurchase, "count", juce::String (balance.available)), celebrationToastMs + 1500);
    }

    lastKnownAvailable = balance.available;
    lastKnownCredits = balance.credits;

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

void TonamorphAudioProcessorEditor::authError (cloud::AuthManager&, const cloud::ApiError& error)
{
    if (loginOverlay.isVisible())
    {
        loginOverlay.setBusy (false);
        loginOverlay.setErrorMessage (userMessageFor (error, ErrorContext::Login));
    }
}

void TonamorphAudioProcessorEditor::timerCallback()
{
    auto& settings = processor.getSettings();

    if (++uiTicks % balanceRefreshTicks == 0)
    {
        auto& auth = processor.getAuthManager();

        if (auth.isLoggedIn() && ! auth.isPollingBalance())
            auth.refreshBalance();
    }

    // The first-sound hint goes away with the first key pressed after it appeared.
    if (firstSoundHintActive && processor.getNoteOnCount() != hintNoteCount)
    {
        firstSoundHintActive = false;
        settings.markSeen (PluginSettings::flagFirstSoundHint);
        keyboard.setHighlightedNote (-1);

        if (toast.isShowing (s (strings::hintFirstSound)))
            toast.hide();

        maybeShowFirstDragHint();
    }
}

//==============================================================================
void TonamorphAudioProcessorEditor::updateFromProcessor()
{
    auto& auth = processor.getAuthManager();
    signInButton.setVisible (! auth.isLoggedIn());
    logoutButton.setVisible (auth.isLoggedIn());
    updateCreditsLabel();
    updateJobStatus();
    updateDetectedKeyAndBpm();
    updateCategoryButtons();
    updateFeedbackBar();
}

void TonamorphAudioProcessorEditor::updateCreditsLabel()
{
    auto& auth = processor.getAuthManager();

    if (! auth.isLoggedIn())
    {
        creditsLabel.setText ({}, juce::dontSendNotification);
        return;
    }

    const auto balance = auth.getBalance();
    creditsLabel.setText (balance.has_value() ? fill (strings::credits, "count", juce::String (balance->available))
                                              : s (strings::creditsUnknown),
                          juce::dontSendNotification);
}

void TonamorphAudioProcessorEditor::updateJobStatus()
{
    using State = cloud::JobClient::State;

    const auto& job = processor.getJobClient();
    const auto state = job.getState();
    const auto stageProgress = juce::jlimit (0.0, 1.0, job.getProgress());
    const auto& result = processor.getCurrentResult();
    const bool hasResult = result.has_value();
    const bool isDemo = hasResult && result->demo;

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
        stageText = error.has_value() ? userMessageFor (*error, ErrorContext::Job) : s (strings::errorMorphFailed);
        stageColour = colours::danger;
    }
    else if (state == State::Cancelled)
    {
        stageText = s (strings::cancelled);
    }
    else if (state == State::Idle)
    {
        stageText = hasResult && ! isDemo ? s (strings::ready) : juce::String();
    }
    else if (state == State::Ready)
    {
        stageText = isDemo ? juce::String() : (job.wasInputTruncated() ? s (strings::truncated) : s (strings::ready));
    }
    else
    {
        stageText = job.getStatusMessage();
    }

    stageLabel.setText (stageText, juce::dontSendNotification);
    stageLabel.setColour (juce::Label::textColourId, stageColour);

    const bool running = job.isRunning();
    cancelJobButton.setVisible (running);
    dropZone.setEnabledForDrop (! running);

    if (running)
        dropZone.setMessage (job.getStatusMessage());
    else if (isDemo)
        dropZone.setMessage (s (strings::emptyDemo));
    else if (hasResult)
        dropZone.setMessage (s (strings::dropAnother));
    else
        dropZone.setMessage (s (strings::dropZone));

    const bool exportable = hasExportableResult();
    dragMidiButton.setEnabled (exportable);
    dragFscButton.setEnabled (exportable);
}

void TonamorphAudioProcessorEditor::updateDetectedKeyAndBpm()
{
    const auto key = processor.getDetectedKey();

    detectedKeyLabel.setText (key.has_value() ? describeKey (*key) : s (strings::keyUnknown), juce::dontSendNotification);
    shakyKeyButton.setVisible (key.has_value() && key->confidence < shakyKeyConfidence);

    if (const auto bpm = processor.getDetectedBpm(); bpm.has_value())
        bpmLabel.setText (fill (strings::bpmValue, "bpm", formatBpm (*bpm)), juce::dontSendNotification);
    else
        bpmLabel.setText (s (strings::bpmUnknown), juce::dontSendNotification);
}

void TonamorphAudioProcessorEditor::updateCategoryButtons()
{
    const int selected = processor.getSelectedCategory();

    for (int i = 0; i < TonamorphAudioProcessor::numCategories; ++i)
        categoryButtons[static_cast<size_t> (i)].setToggleState (i == selected, juce::dontSendNotification);
}

void TonamorphAudioProcessorEditor::updateFeedbackBar()
{
    if (feedbackBar.isShowingOutcome())
        return;

    const bool canRate = processor.canRateCurrentResult() && processor.isCurrentResultPlayable()
                      && ! processor.getJobClient().isRunning();

    if (canRate)
    {
        if (! feedbackBar.isVisible())
            feedbackBar.showPrompt();
    }
    else
    {
        feedbackBar.hideBar();
    }
}

void TonamorphAudioProcessorEditor::onResultEvent()
{
    updateJobStatus();
    updateDetectedKeyAndBpm();
    updateFeedbackBar();

    const auto& result = processor.getCurrentResult();

    if (! result.has_value() || ! processor.isCurrentResultPlayable() || result->demo)
        return;

    auto& settings = processor.getSettings();

    // The day-14 NPS card and the week-one gift count from the first own-clip morph.
    if (! processor.wasCurrentResultRestored())
        settings.markFirstMorph (juce::Time::getCurrentTime());

    // Celebration 1: the first own-clip morph — in-scale keys glow, real key and BPM. The
    // first-sound hint follows once the toast has gone.
    if (! processor.wasCurrentResultRestored() && ! settings.hasSeen (PluginSettings::flagFirstMorph))
    {
        settings.markSeen (PluginSettings::flagFirstMorph);
        keyboard.glowPitchClasses (result->analysis.key.scalePitchClasses, celebrationGlowMs);
        toast.show (fill (strings::fill (strings::celebrateFirstMorph, "key", describeKey (result->analysis.key).toStdString()).c_str(),
                          "bpm", formatBpm (result->analysis.bpm)),
                    celebrationToastMs);

        juce::Component::SafePointer<TonamorphAudioProcessorEditor> safeThis (this);
        juce::Timer::callAfterDelay (celebrationToastMs + 250, [safeThis]
        {
            if (safeThis != nullptr)
                safeThis->showFirstSoundHintIfNeeded();
        });
        return;
    }

    showFirstSoundHintIfNeeded();
}

void TonamorphAudioProcessorEditor::showFirstSoundHintIfNeeded()
{
    auto& settings = processor.getSettings();
    const auto& result = processor.getCurrentResult();

    if (! result.has_value() || result->demo || ! processor.isCurrentResultPlayable())
        return;

    if (settings.hasSeen (PluginSettings::flagFirstSoundHint))
    {
        maybeShowFirstDragHint();
        return;
    }

    if (firstSoundHintActive || toast.isVisible())
        return;

    firstSoundHintActive = true;
    hintNoteCount = processor.getNoteOnCount();
    keyboard.setHighlightedNote (firstSoundNote);
    toast.show (s (strings::hintFirstSound), 0);
}

void TonamorphAudioProcessorEditor::maybeShowFirstDragHint()
{
    auto& settings = processor.getSettings();
    const auto& result = processor.getCurrentResult();

    if (firstDragHintActive || settings.hasSeen (PluginSettings::flagFirstDragHint) || ! hasExportableResult()
        || ! result.has_value() || result->demo || toast.isVisible())
        return;

    firstDragHintActive = true;
    toast.show (s (strings::hintFirstDrag), 0);
}

void TonamorphAudioProcessorEditor::showLoginOverlay (bool show)
{
    if (show)
    {
        showPaywall (false);
        loginOverlay.setErrorMessage ({});
        loginOverlay.toFront (false);
    }

    loginOverlay.setVisible (show);
}

void TonamorphAudioProcessorEditor::showPaywall (bool show)
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
            juce::Component::SafePointer<TonamorphAudioProcessorEditor> safeThis (this);
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

void TonamorphAudioProcessorEditor::openFileChooser()
{
    if (processor.getJobClient().isRunning())
        return;

    fileChooser = std::make_unique<juce::FileChooser> (s (strings::chooseAudioFile),
                                                       juce::File::getSpecialLocation (juce::File::userMusicDirectory),
                                                       cloud::UploadEncoder::getSupportedWildcards());

    juce::Component::SafePointer<TonamorphAudioProcessorEditor> safeThis (this);
    fileChooser->launchAsync (juce::FileBrowserComponent::openMode | juce::FileBrowserComponent::canSelectFiles,
                              [safeThis] (const juce::FileChooser& chooser)
                              {
                                  if (safeThis == nullptr)
                                      return;

                                  if (const auto file = chooser.getResult(); file.existsAsFile())
                                      safeThis->submitAudioFile (file);
                              });
}

void TonamorphAudioProcessorEditor::openSettingsMenu()
{
    constexpr int crashReportsItem = 1;

    juce::PopupMenu menu;
    menu.addItem (crashReportsItem, s (strings::crashReportsOptIn), true, processor.getSettings().isCrashReportingEnabled());

    juce::Component::SafePointer<TonamorphAudioProcessorEditor> safeThis (this);
    menu.showMenuAsync (juce::PopupMenu::Options().withTargetComponent (settingsButton), [safeThis] (int chosen)
    {
        if (safeThis != nullptr && chosen == crashReportsItem)
            safeThis->processor.setCrashReportingEnabled (! safeThis->processor.getSettings().isCrashReportingEnabled());
    });
}

void TonamorphAudioProcessorEditor::showAbout (bool show)
{
    if (show)
    {
        showReferral (false);
        aboutOverlay.setCrashReportingEnabled (processor.getSettings().isCrashReportingEnabled());
        aboutOverlay.toFront (false);
    }

    aboutOverlay.setVisible (show);
}

void TonamorphAudioProcessorEditor::showReferral (bool show)
{
    if (show)
    {
        const auto referral = processor.getAuthManager().getReferral();

        if (! referral.has_value())
            return;

        showAbout (false);
        referralPanel.setReferral (*referral);
        referralPanel.toFront (false);
    }

    referralPanel.setVisible (show);
}

void TonamorphAudioProcessorEditor::updateReferralButton()
{
    auto& auth = processor.getAuthManager();
    const auto referral = auth.getReferral();
    const bool available = auth.isLoggedIn() && referral.has_value();

    if (referralButton.isVisible() != available)
    {
        referralButton.setVisible (available);
        resized();
    }

    if (! available)
        showReferral (false);
    else if (referralPanel.isVisible())
        referralPanel.setReferral (*referral);
}

void TonamorphAudioProcessorEditor::maybeShowNpsCard()
{
    if (npsOffered || npsCard.isVisible() || ! processor.getAuthManager().isLoggedIn())
        return;

    auto& settings = processor.getSettings();
    core::NpsState state;

    if (const auto firstMorphAt = settings.getFirstMorphAt(); firstMorphAt.has_value())
        state.firstMorphAtMs = firstMorphAt->toMilliseconds();

    state.answered = settings.wasNpsAnswered();
    state.dismissals = settings.getNpsDismissals();

    if (! core::shouldShowNpsCard (state, juce::Time::currentTimeMillis()))
        return;

    npsOffered = true;
    npsCard.showCard();
}

void TonamorphAudioProcessorEditor::submitNps (int score, const juce::String& comment)
{
    if (npsRequest != cloud::ApiClient::invalidRequest)
        return;

    npsCard.setBusy (true);
    const auto body = juce::String (core::buildNpsJson (score, comment.toStdString()));

    juce::Component::SafePointer<TonamorphAudioProcessorEditor> safeThis (this);
    npsRequest = processor.getApiClient().postNps (body, [safeThis] (cloud::ApiClient::Response<cloud::NpsResponse> response)
    {
        if (safeThis == nullptr)
            return;

        safeThis->npsRequest = cloud::ApiClient::invalidRequest;
        auto& settings = safeThis->processor.getSettings();

        if (response.ok())
        {
            settings.setNpsAnswered();
            safeThis->npsCard.showOutcome (s (strings::feedbackThanks), false);
        }
        else if (response.statusCode == 409)
        {
            // Already answered within 30 days (contract §14): nothing more to ask.
            settings.setNpsAnswered();
            safeThis->npsCard.hideCard();
        }
        else if (response.statusCode == 404)
        {
            // The route is not deployed yet: try again on a later day, at most once more.
            settings.incrementNpsDismissals();
            safeThis->npsCard.hideCard();
        }
        else
        {
            safeThis->npsCard.showOutcome (s (strings::feedbackFailed), true);
        }
    });
}

bool TonamorphAudioProcessorEditor::weekOneGiftArrived (const cloud::CreditBalance& balance) const
{
    // The server's word when `/v1/me` lists gifts; the balance heuristic otherwise.
    if (const auto& gifts = processor.getAuthManager().getGifts(); ! gifts.isEmpty())
        return gifts.contains (core::weekOneGiftKey);

    if (! lastKnownCredits.has_value())
        return false;

    std::optional<std::int64_t> firstMorphAtMs;

    if (const auto firstMorphAt = processor.getSettings().getFirstMorphAt(); firstMorphAt.has_value())
        firstMorphAtMs = firstMorphAt->toMilliseconds();

    return core::isWeekOneGiftDelta (*lastKnownCredits, balance.credits, firstMorphAtMs, juce::Time::currentTimeMillis());
}

void TonamorphAudioProcessorEditor::setupKnob (juce::Slider& slider, juce::Label& label, const juce::String& text)
{
    slider.setSliderStyle (juce::Slider::RotaryHorizontalVerticalDrag);
    slider.setTextBoxStyle (juce::Slider::TextBoxBelow, false, 76, 18);
    slider.setRotaryParameters (juce::MathConstants<float>::pi * 1.25f, juce::MathConstants<float>::pi * 2.75f, true);

    label.setText (text, juce::dontSendNotification);
    label.setJustificationType (juce::Justification::centred);
    label.setFont (TonamorphLookAndFeel::font (13.0f));
    label.setColour (juce::Label::textColourId, colours::textDim);

    addAndMakeVisible (slider);
    addAndMakeVisible (label);
}

//==============================================================================
void TonamorphAudioProcessorEditor::checkForUpdates()
{
    auto& settings = processor.getSettings();

    if (const auto cached = settings.getCachedVersionInfo(); cached.has_value())
        applyVersionInfo (*cached);

    const auto now = juce::Time::getCurrentTime();
    const auto lastCheck = settings.getLastVersionCheck();

    if (lastCheck <= now && now - lastCheck < juce::RelativeTime::hours (versionCheckHours))
        return;

    if (versionRequest != cloud::ApiClient::invalidRequest)
        return;

    settings.setLastVersionCheck (now);

    juce::Component::SafePointer<TonamorphAudioProcessorEditor> safeThis (this);
    versionRequest = processor.getApiClient().getVersion ([safeThis] (cloud::ApiClient::Response<cloud::VersionInfo> response)
    {
        if (safeThis == nullptr)
            return;

        safeThis->versionRequest = cloud::ApiClient::invalidRequest;

        if (! response.ok())
            return;   // no route yet, offline: the banner simply stays as it was

        safeThis->processor.getSettings().setCachedVersionInfo (*response.value);
        safeThis->applyVersionInfo (*response.value);
    });
}

void TonamorphAudioProcessorEditor::applyVersionInfo (const cloud::VersionInfo& info)
{
    const std::string current = TONAMORPH_VERSION_STRING;
    const bool wasVisible = versionBanner.isVisible();

    if (core::isBelowMinimumVersion (current, info.minSupported.toStdString()))
        versionBanner.showUpdateRequired (info.downloadUrl);
    else if (core::isNewerVersion (info.latest.toStdString(), current)
             && processor.getSettings().getDismissedUpdateVersion() != info.latest)
        versionBanner.showUpdateAvailable (info.latest, info.downloadUrl);
    else
        versionBanner.hide();

    if (wasVisible != versionBanner.isVisible())
        resized();
}

//==============================================================================
void TonamorphAudioProcessorEditor::submitAudioFile (const juce::File& file)
{
    auto& auth = processor.getAuthManager();

    if (! auth.isLoggedIn())
    {
        // First drop while signed out: keep the clip, ask for the account, morph after.
        pendingDropFile = file;
        loginOverlay.setMessage (s (strings::signInToMorph));
        showLoginOverlay (true);
        return;
    }

    if (auth.getBalance().has_value() && auth.getAvailableCredits() <= 0)
    {
        paywallDismissed = false;
        showPaywall (true);
        return;
    }

    toast.hide();
    keyboard.clearOverlays();
    firstSoundHintActive = false;
    firstDragHintActive = false;
    processor.submitAudioFile (file);
}

bool TonamorphAudioProcessorEditor::hasExportableResult() const
{
    const auto& result = processor.getCurrentResult();
    return result.has_value() && ! result->midi.tracks.empty();
}

juce::File TonamorphAudioProcessorEditor::writeExport (bool midi)
{
    const auto& result = processor.getCurrentResult();

    if (! result.has_value())
        return {};

    const auto baseName = exporting::MidiExporter::suggestedBaseName (*result);

    return midi ? exporting::MidiExporter::writeExportFile (*result, baseName)
                : exporting::FscExporter::writeExportFile (*result, baseName);
}

void TonamorphAudioProcessorEditor::openExportSaveDialog (bool midi)
{
    const auto& result = processor.getCurrentResult();

    if (! result.has_value())
        return;

    const juce::String extension = midi ? exporting::MidiExporter::extension : exporting::FscExporter::extension;
    const auto initialFile = juce::File::getSpecialLocation (juce::File::userDocumentsDirectory)
                                 .getChildFile (exporting::MidiExporter::suggestedBaseName (*result) + extension);

    fileChooser = std::make_unique<juce::FileChooser> (midi ? s (strings::saveMidiFile) : s (strings::saveFscFile),
                                                       initialFile, "*" + extension);

    juce::Component::SafePointer<TonamorphAudioProcessorEditor> safeThis (this);
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

                                  safeThis->stageLabel.setText (fill (written ? strings::savedFile : strings::couldNotWrite,
                                                                      "file", target.getFileName()),
                                                                juce::dontSendNotification);
                                  safeThis->stageLabel.setColour (juce::Label::textColourId,
                                                                  written ? colours::textDim : colours::danger);
                              });
}

void TonamorphAudioProcessorEditor::onExportDragFinished (bool midi, bool landedOutside)
{
    if (! landedOutside)
        return;

    auto& settings = processor.getSettings();

    if (firstDragHintActive)
    {
        firstDragHintActive = false;

        if (toast.isShowing (s (strings::hintFirstDrag)))
            toast.hide();
    }

    settings.markSeen (PluginSettings::flagFirstDragHint);

    // Celebration 2: the first .mid landing in the DAW — the export target pulses.
    if (midi && ! settings.hasSeen (PluginSettings::flagFirstDrag))
    {
        settings.markSeen (PluginSettings::flagFirstDrag);
        dragMidiButton.pulse();
        toast.show (s (strings::celebrateFirstDrag), celebrationToastMs);
    }
}

} // namespace tonamorph
