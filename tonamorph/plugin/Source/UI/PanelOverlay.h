#pragma once

/**
 * A dimmed backdrop with one centred rounded panel: the base of the About screen and the
 * referral share. Subclasses lay out their children inside getPanelBounds(); a click on
 * the backdrop fires onClose. Message thread.
 */

#include <JuceHeader.h>

#include "UI/TonamorphLookAndFeel.h"

#include <functional>

namespace tonamorph::ui
{

class PanelOverlay : public juce::Component
{
public:
    PanelOverlay (int preferredPanelWidth, int preferredPanelHeight)
        : panelWidth (preferredPanelWidth), panelHeight (preferredPanelHeight)
    {
    }

    std::function<void()> onClose;

    void paint (juce::Graphics& g) override
    {
        g.fillAll (colours::background.withAlpha (0.94f));

        const auto panel = getPanelBounds().toFloat();
        g.setColour (colours::panel);
        g.fillRoundedRectangle (panel, 10.0f);
        g.setColour (colours::outline);
        g.drawRoundedRectangle (panel, 10.0f, 1.0f);
    }

    void mouseUp (const juce::MouseEvent& event) override
    {
        if (! getPanelBounds().contains (event.getPosition()))
            requestClose();
    }

protected:
    /** The panel, centred and never larger than the window minus a margin. */
    juce::Rectangle<int> getPanelBounds() const
    {
        return getLocalBounds().withSizeKeepingCentre (juce::jmin (panelWidth, getWidth() - 32),
                                                       juce::jmin (panelHeight, getHeight() - 24));
    }

    void requestClose()
    {
        if (onClose != nullptr)
            onClose();
    }

private:
    int panelWidth;
    int panelHeight;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR (PanelOverlay)
};

} // namespace tonamorph::ui
