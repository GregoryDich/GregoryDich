#include "Export/FscExporter.h"

#include "Core/FscWriter.h"
#include "Export/DragExport.h"

namespace snapplay::exporting
{

juce::MemoryBlock FscExporter::toMemoryBlock (const std::vector<core::Track>& tracks, double bpm)
{
    const auto bytes = core::writeFsc (tracks, bpm, ppq);
    return juce::MemoryBlock (bytes.data(), bytes.size());
}

bool FscExporter::writeToFile (const std::vector<core::Track>& tracks, double bpm, const juce::File& destination)
{
    juce::ignoreUnused (tracks, bpm, destination);
    return false;
}

juce::File FscExporter::writeExportFile (const cloud::JobResult& result, const juce::String& baseName)
{
    juce::ignoreUnused (result, baseName);
    return {};
}

} // namespace snapplay::exporting
