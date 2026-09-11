#pragma once

/**
 * The plugin window. Sections, top to bottom:
 *   version banner (only when an update is available or required)
 *   · header (title, settings menu, credit balance, sign in / log out)
 *   · drop zone (file drag & drop / browse) · progress and stage line
 *   · category buttons (Bass/Drums/Synth/Vocals)
 *   · Scale-Snap mode + root selectors with the detected-key label (and the "shaky key"
 *     picker when confidence is low), BPM label
 *   · ADSR + filter + gain knobs, root target, drum mode
 *   · "Drag .mid" / "Drag .fsc" export buttons with the result-feedback bar
 *   · on-screen MIDI keyboard, with a floating toast for hints and celebrations.
 * Overlays: LoginOverlay when signing in (opened by the header button or by dropping a
 * clip while signed out — the demo morph plays without an account), PaywallPrompt when
 * available credits reach 0 (contract §3, GTM §2.4), AboutOverlay (version, website,
 * crash-report opt-in, third-party notices) from the header's About button, ReferralPanel
 * ("Send a morph to a friend") from a header button that exists only while `/v1/me`
 * carries `referral.url`, and the non-modal NpsCard 14 days after the first own-clip
 * morph. The week-one gift toast is inferred from the balance poll (weekOneGiftArrived).
 * Every user-facing string comes from Core/Strings.h.
 *
 * The editor is the FileDragAndDropTarget for the whole window and the
 * DragAndDropContainer for the export buttons. All callbacks run on the message thread.
 */

#include <JuceHeader.h>

#include "Cloud/AuthManager.h"
#include "Cloud/Models.h"
#include "PluginProcessor.h"
#include "UI/AboutOverlay.h"
#include "UI/FeedbackBar.h"
#include "UI/MessageToast.h"
#include "UI/NpsCard.h"
#include "UI/ReferralPanel.h"
#include "UI/ScaleKeyboard.h"
#include "UI/TonamorphLookAndFeel.h"
#include "UI/VersionBanner.h"

#include <array>
#include <cstdint>
#include <functional>
#include <memory>
#include <optional>
#include <vector>

namespace tonamorph
{

//==============================================================================
/** GTM §2.4 paywall: the exact state ("That was your last free morph. Nothing happens
    unless you buy."), one equally sized button per offer plus "Not now", the expiry
    disclosure for the subscription and "never expire" for packs. Counts and prices come
    from `/v1/plans` when present, else from the strings table. No countdowns, no scarcity.
    The owner polls the balance while this is visible. */
class PaywallPrompt final : public juce::Component
{
public:
    PaywallPrompt();

    /** Fills the buttons from `/v1/plans`: the first credit pack and the first subscription. */
    void setPlans (const std::vector<cloud::PlanInfo>& plans);

    /** Invoked with the chosen plan (nullptr when no plan is known yet); the default handler
        opens `checkoutUrl`, or the website when there is none. */
    std::function<void (const cloud::PlanInfo*)> onCheckout;
    std::function<void()> onDismiss;

    void paint (juce::Graphics& g) override;
    void resized() override;

private:
    void rebuild();
    /** First plan of the requested kind (subscription or credit pack), or nullptr. */
    const cloud::PlanInfo* findPlan (bool subscription) const;
    juce::Rectangle<int> getPanelBounds() const;

    juce::Label headlineLabel;
    juce::TextButton buyPackButton;
    juce::Label packLine;
    juce::TextButton subscribeButton;
    juce::Label subscriptionLine;
    juce::TextButton dismissButton;
    std::vector<cloud::PlanInfo> plans;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR (PaywallPrompt)
};

//==============================================================================
/** Email + password sign-in (contract §1). Account creation and password recovery need a
    browser (email confirmation), so the overlay only links to the website's `/signup` and
    `/reset-password` pages. Dismissible: the demo morph plays without an account. */
class LoginOverlay final : public juce::Component
{
public:
    LoginOverlay();

    std::function<void (const juce::String& email, const juce::String& password)> onLogin;
    std::function<void()> onDismiss;

    /** Disables the form while a request is in flight. */
    void setBusy (bool busy);
    void setErrorMessage (const juce::String& message);
    /** The line under the title, e.g. "Sign in to morph your own clips. 3 free." */
    void setMessage (const juce::String& message);
    void clearForm();

    void paint (juce::Graphics& g) override;
    void resized() override;

private:
    void submit();
    juce::Rectangle<int> getPanelBounds() const;

    juce::Label titleLabel;
    juce::Label messageLabel;
    juce::Label emailLabel;
    juce::TextEditor emailEditor;
    juce::Label passwordLabel;
    juce::TextEditor passwordEditor;
    juce::TextButton loginButton;
    juce::Label statusLabel;
    juce::HyperlinkButton signupLink;
    juce::HyperlinkButton forgotPasswordLink;
    juce::TextButton dismissButton;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR (LoginOverlay)
};

//==============================================================================
/** The drop target's visual: dashed frame, instruction text, highlighted during a drag,
    click to browse. */
class DropZone final : public juce::Component
{
public:
    DropZone();

    std::function<void()> onBrowse;

    void setMessage (const juce::String& message);
    void setHighlighted (bool highlighted);
    void setEnabledForDrop (bool enabled);

    void paint (juce::Graphics& g) override;
    void resized() override;
    void mouseUp (const juce::MouseEvent& event) override;

private:
    juce::Label messageLabel;
    bool highlighted = false;
    bool dropEnabled = true;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR (DropZone)
};

//==============================================================================
/** A button that starts an external file drag when dragged; `fileProvider` writes the
    export on demand and returns the file (a non-existent File aborts the drag).
    `onDragFinished (landedOutside)` fires when the drag ends; `landedOutside` is true when
    the pointer let go outside the plugin window, i.e. in the DAW. */
class ExportDragButton final : public juce::TextButton
{
public:
    explicit ExportDragButton (const juce::String& buttonText);

    std::function<juce::File()> fileProvider;
    std::function<void (bool landedOutside)> onDragFinished;

    /** Brief accent flash (the first-drag celebration). */
    void pulse();

    void mouseDown (const juce::MouseEvent& event) override;
    void mouseDrag (const juce::MouseEvent& event) override;
    void mouseUp (const juce::MouseEvent& event) override;

private:
    bool dragStarted = false;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR (ExportDragButton)
};

//==============================================================================
class TonamorphAudioProcessorEditor final : public juce::AudioProcessorEditor,
                                           public juce::FileDragAndDropTarget,
                                           public juce::DragAndDropContainer,
                                           private juce::ChangeListener,
                                           private cloud::AuthManager::Listener,
                                           private juce::Timer
{
public:
    static constexpr int defaultWidth = 920;
    static constexpr int defaultHeight = 640;

    explicit TonamorphAudioProcessorEditor (TonamorphAudioProcessor& processor);
    ~TonamorphAudioProcessorEditor() override;

    void paint (juce::Graphics& g) override;
    void resized() override;

    //==============================================================================
    bool isInterestedInFileDrag (const juce::StringArray& files) override;
    void fileDragEnter (const juce::StringArray& files, int x, int y) override;
    void fileDragExit (const juce::StringArray& files) override;
    void filesDropped (const juce::StringArray& files, int x, int y) override;

private:
    using SliderAttachment = juce::AudioProcessorValueTreeState::SliderAttachment;
    using ComboBoxAttachment = juce::AudioProcessorValueTreeState::ComboBoxAttachment;
    using ButtonAttachment = juce::AudioProcessorValueTreeState::ButtonAttachment;

    void changeListenerCallback (juce::ChangeBroadcaster* source) override;
    void authStateChanged (cloud::AuthManager&) override;
    void balanceChanged (cloud::AuthManager&, const cloud::CreditBalance& balance) override;
    void authError (cloud::AuthManager&, const cloud::ApiError& error) override;
    void timerCallback() override;

    /** Refreshes every label/button from processor state. */
    void updateFromProcessor();
    void updateCreditsLabel();
    void updateJobStatus();
    void updateDetectedKeyAndBpm();
    void updateCategoryButtons();
    void updateFeedbackBar();
    /** Reacts to the processor's result events: celebrations and hints. */
    void onResultEvent();
    void showLoginOverlay (bool show);
    /** Shows the paywall (fetching /v1/plans first) and starts balance polling. */
    void showPaywall (bool show);
    void openFileChooser();
    void openSettingsMenu();
    void showAbout (bool show);
    void showReferral (bool show);
    /** The header's "Send a morph to a friend" exists only with a `referral.url` from `/v1/me`. */
    void updateReferralButton();
    /** The day-14 NPS card (core::shouldShowNpsCard): offered once per editor session, signed in. */
    void maybeShowNpsCard();
    /** POST /v1/nps; a 409 counts as answered, a 404 as one dismissal. */
    void submitNps (int score, const juce::String& comment);
    /** The week-one gift: the server's `gifts` list when it sends one, otherwise the balance
        heuristic core::isWeekOneGiftDelta — one function, so the heuristic can be retired. */
    bool weekOneGiftArrived (const cloud::CreditBalance& balance) const;
    void setupKnob (juce::Slider& slider, juce::Label& label, const juce::String& text);

    /** GET /v1/version at most once per 24 h; applies the cached answer meanwhile. */
    void checkForUpdates();
    void applyVersionInfo (const cloud::VersionInfo& info);

    /** Submits through the processor; signed out, opens the sign-in and keeps the file. */
    void submitAudioFile (const juce::File& file);
    bool hasExportableResult() const;
    /** Writes the current result to the export directory (`.mid` or `.fsc`). */
    juce::File writeExport (bool midi);
    void openExportSaveDialog (bool midi);
    void onExportDragFinished (bool midi, bool landedOutside);
    /** "Ready. Play C3 — that's your bass, in key." with C3 highlighted, once per person. */
    void showFirstSoundHintIfNeeded();
    void maybeShowFirstDragHint();
    void placeToast();

    // Declared first so it outlives every component that uses it.
    ui::TonamorphLookAndFeel lookAndFeel;

    TonamorphAudioProcessor& processor;

    // Banner + header
    ui::VersionBanner versionBanner;
    juce::Label titleLabel;
    juce::TextButton settingsButton;
    juce::TextButton aboutButton;
    juce::TextButton referralButton;
    juce::Label creditsLabel;
    juce::TextButton signInButton;
    juce::TextButton logoutButton;

    // Input
    DropZone dropZone;
    double progressValue = 0.0;
    juce::ProgressBar progressBar;
    juce::Label stageLabel;
    juce::TextButton cancelJobButton;
    std::unique_ptr<juce::FileChooser> fileChooser;
    juce::File pendingDropFile;   ///< dropped while signed out; submitted after sign-in

    // Category
    std::array<juce::TextButton, TonamorphAudioProcessor::numCategories> categoryButtons;
    std::unique_ptr<juce::ParameterAttachment> categoryAttachment;

    // Scale-Snap
    juce::Label scaleModeLabel;
    juce::ComboBox scaleModeBox;
    juce::Label scaleRootLabel;
    juce::ComboBox scaleRootBox;
    juce::Label detectedKeyLabel;
    juce::TextButton shakyKeyButton;
    juce::Label bpmLabel;
    std::unique_ptr<ComboBoxAttachment> scaleModeAttachment;
    std::unique_ptr<ComboBoxAttachment> scaleRootAttachment;

    // Sound
    juce::Slider attackKnob, decayKnob, sustainKnob, releaseKnob, cutoffKnob, resonanceKnob, gainKnob, rootTargetKnob;
    juce::Label attackLabel, decayLabel, sustainLabel, releaseLabel, cutoffLabel, resonanceLabel, gainLabel, rootTargetLabel;
    juce::ToggleButton drumModeButton;
    std::unique_ptr<SliderAttachment> attackAttachment, decayAttachment, sustainAttachment, releaseAttachment,
                                      cutoffAttachment, resonanceAttachment, gainAttachment, rootTargetAttachment;
    std::unique_ptr<ButtonAttachment> drumModeAttachment;

    // Export + feedback
    ExportDragButton dragMidiButton;
    ExportDragButton dragFscButton;
    ui::FeedbackBar feedbackBar;

    // Keyboard + toast
    ui::ScaleKeyboard keyboard;
    ui::MessageToast toast;

    // Overlays
    LoginOverlay loginOverlay;
    PaywallPrompt paywallPrompt;
    ui::AboutOverlay aboutOverlay;
    ui::ReferralPanel referralPanel;
    ui::NpsCard npsCard;
    cloud::ApiClient::RequestId plansRequest = cloud::ApiClient::invalidRequest;
    cloud::ApiClient::RequestId versionRequest = cloud::ApiClient::invalidRequest;
    cloud::ApiClient::RequestId npsRequest = cloud::ApiClient::invalidRequest;
    /** Set by "Not now": the prompt stays hidden until credits change or a job is refused. */
    bool paywallDismissed = false;
    bool npsOffered = false;   ///< the card is offered at most once per editor session

    // Onboarding state (persisted flags live in PluginSettings)
    std::optional<int> lastKnownAvailable;   ///< for purchase detection by the balance poll
    std::optional<int> lastKnownCredits;     ///< `balance.credits` for the week-one gift heuristic
    bool firstSoundHintActive = false;
    bool firstDragHintActive = false;
    std::uint32_t hintNoteCount = 0;
    int uiTicks = 0;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR (TonamorphAudioProcessorEditor)
};

} // namespace tonamorph
