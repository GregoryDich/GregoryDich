#include "Export/FscExporter.h"

#include "Core/FscWriter.h"
#include "Export/DragExport.h"

namespace tonamorph::exporting
{

juce::MemoryBlock FscExporter::toMemoryBlock (const std::vector<core::Track>& tracks, double bpm)
{
    const auto bytes = core::writeFsc (tracks, bpm, ppq);
    return juce::MemoryBlock (bytes.data(), bytes.size());
}

bool FscExporter::writeToFile (const std::vector<core::Track>& tracks, double bpm, const juce::File& destination)
{
    return DragExport::writeBytes (core::writeFsc (tracks, bpm, ppq), destination);
}

juce::File FscExporter::writeExportFile (const cloud::JobResult& result, const juce::String& baseName)
{
    const auto destination = DragExport::exportFileFor (baseName, extension);

    if (! writeToFile (result.midi.tracks, result.analysis.bpm, destination))
        return {};

    return destination;
}

} // namespace tonamorph::exporting
