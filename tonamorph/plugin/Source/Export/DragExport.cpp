#include "Export/DragExport.h"

#include "Core/Strings.h"

namespace tonamorph::exporting
{

juce::File DragExport::exportDirectory()
{
    auto directory = juce::File::getSpecialLocation (juce::File::tempDirectory)
                         .getChildFile (strings::productName)
                         .getChildFile ("exports");
    directory.createDirectory();
    return directory;
}

juce::File DragExport::exportFileFor (const juce::String& baseName, const juce::String& extension)
{
    auto legalName = juce::File::createLegalFileName (baseName.trim());

    if (legalName.isEmpty())
        legalName = "tonamorph";

    return exportDirectory().getChildFile (legalName + extension);
}

bool DragExport::writeBytes (const std::vector<std::uint8_t>& bytes, const juce::File& destination)
{
    if (bytes.empty() || destination == juce::File())
        return false;

    if (! destination.getParentDirectory().createDirectory().wasOk())
        return false;

    return destination.replaceWithData (bytes.data(), bytes.size());
}

bool DragExport::startFileDrag (const juce::File& file, juce::Component* sourceComponent,
                                std::function<void()> onFinished)
{
    if (sourceComponent == nullptr || ! file.existsAsFile())
        return false;

    if (juce::DragAndDropContainer::findParentDragContainerFor (sourceComponent) == nullptr)
        return false;

    return juce::DragAndDropContainer::performExternalDragDropOfFiles (juce::StringArray { file.getFullPathName() },
                                                                      false, sourceComponent, std::move (onFinished));
}

void DragExport::cleanupOldExports (juce::RelativeTime maxAge)
{
    const auto cutoff = juce::Time::getCurrentTime() - maxAge;

    for (const auto& entry : juce::RangedDirectoryIterator (exportDirectory(), false, "*", juce::File::findFiles))
        if (entry.getModificationTime() < cutoff)
            entry.getFile().deleteFile();
}

} // namespace tonamorph::exporting
