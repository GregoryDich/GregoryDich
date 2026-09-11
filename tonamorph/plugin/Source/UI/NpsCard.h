#pragma once

/**
 * The day-14 NPS card (GTM Appendix B §5): "How likely are you to recommend Tonamorph?
 * 0–10" with eleven score buttons, an optional comment and Send / Not now. Non-modal, it
 * floats over the keyboard; the editor decides when to show it (core::shouldShowNpsCard)
 * and where the answer goes (`POST /v1/nps`). Message thread.
 */

#include <JuceHeader.h>

#include <array>
#include <functional>

namespace tonamorph::ui
{

class NpsCard final : public juce::Component,
                      private juce::Timer
{
public:
    static constexpr int preferredHeight = 152;

    NpsCard();
    ~NpsCard() override;

    std::function<void (int score, const juce::String& comment)> onSubmit;
    std::function<void()> onDismiss;

    /** Resets the selection and comment and shows the card. */
    void showCard();
    /** Shows `message` for a few seconds, then returns to the question (`keepControl`) or hides. */
    void showOutcome (const juce::String& message, bool keepControl);
    /** Disables the controls while the request is in flight. */
    void setBusy (bool busy);
    void hideCard();

    void paint (juce::Graphics& g) override;
    void resized() override;

private:
    void timerCallback() override;
    void selectScore (int score);
    void setShowingOutcome (bool showing);

    static constexpr int outcomeVisibleMs = 3500;
    static constexpr int numScores = 11;

    juce::Label questionLabel;
    std::array<juce::TextButton, numScores> scoreButtons;
    juce::TextEditor commentEditor;
    juce::TextButton sendButton;
    juce::TextButton dismissButton;
    juce::Label outcomeLabel;
    int selectedScore = -1;
    bool returnToQuestionAfterOutcome = false;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR (NpsCard)
};

} // namespace tonamorph::ui
