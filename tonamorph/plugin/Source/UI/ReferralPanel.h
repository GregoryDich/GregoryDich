#pragma once

/**
 * "Send a morph to a friend" (GTM §2.4): the account's share link from `/v1/me`
 * (`referral.url`) with a Copy button, the promise line and, once a friend joined, what
 * the link earned. Message thread.
 */

#include <JuceHeader.h>

#include "Cloud/Models.h"
#include "UI/PanelOverlay.h"

namespace tonamorph::ui
{

class ReferralPanel final : public PanelOverlay,
                            private juce::Timer
{
public:
    ReferralPanel();
    ~ReferralPanel() override;

    void setReferral (const cloud::ReferralInfo& referral);

    void resized() override;

private:
    void timerCallback() override;

    static constexpr int copiedVisibleMs = 1800;

    juce::Label titleLabel;
    juce::Label promiseLabel;
    juce::TextEditor urlEditor;
    juce::TextButton copyButton;
    juce::Label copiedLabel;
    juce::Label statsLabel;
    juce::TextButton closeButton;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR (ReferralPanel)
};

} // namespace tonamorph::ui
