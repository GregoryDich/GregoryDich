#pragma once

/**
 * Thumbs up / down on a completed morph (GTM Appendix B §5). A thumbs-down opens the
 * reason list (bleed, wrong key, MIDI off, clicks, slow, other) with an optional note of
 * at most 140 characters and a Send button; the bar shows the outcome and then hides, so
 * each job is rated once. Message thread.
 */

#include <JuceHeader.h>

#include <functional>

namespace tonamorph::ui
{

class FeedbackBar final : public juce::Component,
                          private juce::Timer
{
public:
    static constexpr int noteLimit = 140;

    enum class Mode { Prompt, Reasons, Outcome };

    FeedbackBar();
    ~FeedbackBar() override;

    /** `reason` is a contract code ("bleed", …) or empty for a thumbs-up. */
    std::function<void (bool thumbsUp, const juce::String& reason, const juce::String& note)> onSubmit;

    /** Shows the prompt state ("How was this morph?" + the two thumbs). */
    void showPrompt();
    /** Shows `message` for a few seconds, then returns to the prompt (`keepControl`) or hides. */
    void showOutcome (const juce::String& message, bool keepControl);
    /** Disables the controls while a request is in flight. */
    void setBusy (bool busy);
    void hideBar();
    bool isShowingOutcome() const noexcept { return isVisible() && mode == Mode::Outcome; }

    void resized() override;

private:
    void timerCallback() override;
    void setMode (Mode newMode);
    void sendDown();

    Mode mode = Mode::Prompt;
    bool returnToPromptAfterOutcome = false;

    juce::Label promptLabel;
    juce::TextButton upButton;
    juce::TextButton downButton;
    juce::ComboBox reasonBox;
    juce::TextEditor noteEditor;
    juce::TextButton sendButton;
    juce::Label outcomeLabel;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR (FeedbackBar)
};

} // namespace tonamorph::ui
