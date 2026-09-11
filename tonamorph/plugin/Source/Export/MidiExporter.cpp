#include "Export/MidiExporter.h"

#include "Core/MidiFileWriter.h"
#include "Export/DragExport.h"

namespace tonamorph::exporting
{

juce::MemoryBlock MidiExporter::toMemoryBlock (const std::vector<core::Track>& tracks, double bpm)
{
    const auto bytes = core::writeMidiFile (tracks, bpm, ppq);
    return juce::MemoryBlock (bytes.data(), bytes.size());
}

bool MidiExporter::writeToFile (const std::vector<core::Track>& tracks, double bpm, const juce::File& destination)
{
    return DragExport::writeBytes (core::writeMidiFile (tracks, bpm, ppq), destination);
}

juce::File MidiExporter::writeExportFile (const cloud::JobResult& result, const juce::String& baseName)
{
    const auto destination = DragExport::exportFileFor (baseName, extension);

    if (! writeToFile (result.midi.tracks, result.analysis.bpm, destination))
        return {};

    return destination;
}

juce::String MidiExporter::suggestedBaseName (const cloud::JobResult& result)
{
    return "tonamorph_" + result.jobId.substring (0, 8);
}

} // namespace tonamorph::exporting
