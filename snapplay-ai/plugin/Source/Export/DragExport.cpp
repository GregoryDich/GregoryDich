#include "Export/DragExport.h"

namespace snapplay::exporting
{

juce::File DragExport::exportDirectory()
{
    auto directory = juce::File::getSpecialLocation (juce::File::tempDirectory)
                         .getChildFile ("SnapPlayAI")
                         .getChildFile ("exports");
    directory.createDirectory();
    return directory;
}

bool DragExport::startFileDrag (const juce::File& file, juce::Component* sourceComponent,
                                std::function<void()> onFinished)
{
    juce::ignoreUnused (file, sourceComponent, onFinished);
    return false;
}

void DragExport::cleanupOldExports (juce::RelativeTime maxAge)
{
    juce::ignoreUnused (maxAge);
}

} // namespace snapplay::exporting
