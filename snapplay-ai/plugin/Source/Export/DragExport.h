#pragma once

/**
 * Drag-to-DAW helpers: a temporary export directory and the external file drag
 * (juce::DragAndDropContainer::performExternalDragDropOfFiles) used by the
 * "Drag .mid" / "Drag .fsc" buttons.
 */

#include <JuceHeader.h>

#include <functional>

namespace snapplay::exporting
{

class DragExport
{
public:
    /** `<temp>/SnapPlayAI/exports`, created on first use. Exported files live here so the
        DAW can copy them during the drop. */
    static juce::File exportDirectory();

    /** Starts a non-modal external drag of `file` (copy semantics). Must be called from a
        mouse-drag callback on the message thread. `onFinished` fires when the drag ends,
        regardless of where it was dropped. Returns false when the platform refused. */
    static bool startFileDrag (const juce::File& file, juce::Component* sourceComponent,
                               std::function<void()> onFinished = {});

    /** Deletes exported files older than `maxAge` (default 24 h). */
    static void cleanupOldExports (juce::RelativeTime maxAge = juce::RelativeTime::hours (24));

private:
    DragExport() = delete;
};

} // namespace snapplay::exporting
