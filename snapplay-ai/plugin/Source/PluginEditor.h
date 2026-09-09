#pragma once

/**
 * The plugin window. Sections, top to bottom:
 *   header (title, credit balance, log-out) · drop zone (file drag & drop / browse)
 *   · progress and stage line · category buttons (Bass/Drums/Synth/Vocals)
 *   · Scale-Snap mode + root selectors with the detected-key label, BPM label
 *   · ADSR + filter + gain knobs, root target, drum mode
 *   · "Drag .mid" / "Drag .fsc" export buttons · on-screen MIDI keyboard.
 * Overlays: LoginOverlay when signed out, PaywallPrompt when available credits reach 0
 * (contract §3).
 *
 * The editor is the FileDragAndDropTarget for the whole window and the
 * DragAndDropContainer for the export buttons. All callbacks run on the message thread.
 */

#include <JuceHeader.h>

#include "Cloud/AuthManager.h"
#include "Cloud/Models.h"
#include "PluginProcessor.h"
#include "UI/SnapPlayLookAndFeel.h"

#include <array>
#include <functional>
#include <memory>
#include <vector>

namespace snapplay
{

//==============================================================================
/** Contract §3 paywall: "You've used your 3 free credits — unlock 50 more for $9, or
    subscribe for $7.99/mo", with buttons opening the plans' `checkout_url` in the system
    browser. The owner polls the balance while this is visible. */
class PaywallPrompt final : public juce::Component
{
public:
    PaywallPrompt();

    /** Builds the message and buttons from `/v1/plans`. The first credit pack and the first
        subscription plan get a button each; plans without a checkout URL are ignored. */
    void setPlans (const std::vector<cloud::PlanInfo>& plans);
    /** Number of free credits mentioned in the message (default 3). */
    void setFreeCredits (int credits);

    /** Invoked with the chosen plan; the default handler opens `checkoutUrl` in the browser. */
    std::function<void (const cloud::PlanInfo&)> onCheckout;
    std::function<void()> onDismiss;

    void paint (juce::Graphics& g) override;
    void resized() override;

private:
    void rebuildMessage();
    /** First purchasable plan of the requested kind (subscription or credit pack), or nullptr. */
    const cloud::PlanInfo* findPlan (bool subscription) const;
    juce::Rectangle<int> getPanelBounds() const;

    juce::Label titleLabel;
    juce::Label messageLabel;
    juce::TextButton buyPackButton;
    juce::TextButton subscribeButton;
    juce::TextButton dismissButton;
    std::vector<cloud::PlanInfo> plans;
    int freeCredits = 3;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR (PaywallPrompt)
};

//==============================================================================
/** Email + password sign-in covering the editor while logged out (contract §1). Account
    creation and password recovery need a browser (email confirmation), so the overlay only
    links to the website's `/signup` and `/reset-password` pages. */
class LoginOverlay final : public juce::Component
{
public:
    LoginOverlay();

    std::function<void (const juce::String& email, const juce::String& password)> onLogin;

    /** Disables the form while a request is in flight. */
    void setBusy (bool busy);
    void setErrorMessage (const juce::String& message);
    void clearForm();

    void paint (juce::Graphics& g) override;
    void resized() override;

private:
    void submit();
    juce::Rectangle<int> getPanelBounds() const;

    juce::Label titleLabel;
    juce::Label emailLabel;
    juce::TextEditor emailEditor;
    juce::Label passwordLabel;
    juce::TextEditor passwordEditor;
    juce::TextButton loginButton;
    juce::Label statusLabel;
    juce::HyperlinkButton signupLink;
    juce::HyperlinkButton forgotPasswordLink;

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
    export on demand and returns the file (a non-existent File aborts the drag). */
class ExportDragButton final : public juce::TextButton
{
public:
    explicit ExportDragButton (const juce::String& buttonText);

    std::function<juce::File()> fileProvider;

    void mouseDown (const juce::MouseEvent& event) override;
    void mouseDrag (const juce::MouseEvent& event) override;
    void mouseUp (const juce::MouseEvent& event) override;

private:
    bool dragStarted = false;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR (ExportDragButton)
};

//==============================================================================
class SnapPlayAudioProcessorEditor final : public juce::AudioProcessorEditor,
                                           public juce::FileDragAndDropTarget,
                                           public juce::DragAndDropContainer,
                                           private juce::ChangeListener,
                                           private cloud::AuthManager::Listener,
                                           private juce::Timer
{
public:
    static constexpr int defaultWidth = 920;
    static constexpr int defaultHeight = 640;

    explicit SnapPlayAudioProcessorEditor (SnapPlayAudioProcessor& processor);
    ~SnapPlayAudioProcessorEditor() override;

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
    void showLoginOverlay (bool show);
    /** Shows the paywall (fetching /v1/plans first) and starts balance polling. */
    void showPaywall (bool show);
    void openFileChooser();
    void setupKnob (juce::Slider& slider, juce::Label& label, const juce::String& text);

    /** Submits through the processor, or shows the paywall when the known balance is 0. */
    void submitAudioFile (const juce::File& file);
    bool hasExportableResult() const;
    /** Writes the current result to the export directory (`.mid` or `.fsc`). */
    juce::File writeExport (bool midi);
    void openExportSaveDialog (bool midi);

    // Declared first so it outlives every component that uses it.
    ui::SnapPlayLookAndFeel lookAndFeel;

    SnapPlayAudioProcessor& processor;

    // Header
    juce::Label titleLabel;
    juce::Label creditsLabel;
    juce::TextButton logoutButton;

    // Input
    DropZone dropZone;
    double progressValue = 0.0;
    juce::ProgressBar progressBar;
    juce::Label stageLabel;
    juce::TextButton cancelJobButton;
    std::unique_ptr<juce::FileChooser> fileChooser;

    // Category
    std::array<juce::TextButton, SnapPlayAudioProcessor::numCategories> categoryButtons;
    std::unique_ptr<juce::ParameterAttachment> categoryAttachment;

    // Scale-Snap
    juce::Label scaleModeLabel;
    juce::ComboBox scaleModeBox;
    juce::Label scaleRootLabel;
    juce::ComboBox scaleRootBox;
    juce::Label detectedKeyLabel;
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

    // Export
    ExportDragButton dragMidiButton;
    ExportDragButton dragFscButton;

    // Keyboard
    juce::MidiKeyboardComponent keyboard;

    // Overlays
    LoginOverlay loginOverlay;
    PaywallPrompt paywallPrompt;
    cloud::ApiClient::RequestId plansRequest = cloud::ApiClient::invalidRequest;
    /** Set by "Not now": the prompt stays hidden until credits change or a job is refused. */
    bool paywallDismissed = false;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR (SnapPlayAudioProcessorEditor)
};

} // namespace snapplay
