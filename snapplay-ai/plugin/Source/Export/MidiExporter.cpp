#include "Export/MidiExporter.h"

#include "Core/MidiFileWriter.h"
#include "Export/DragExport.h"

namespace snapplay::exporting
{

juce::MemoryBlock MidiExporter::toMemoryBlock (const std::vector<core::Track>& tracks, double bpm)
{
    const auto bytes = core::writeMidiFile (tracks, bpm, ppq);
    return juce::MemoryBlock (bytes.data(), bytes.size());
}

bool MidiExporter::writeToFile (const std::vector<core::Track>& tracks, double bpm, const juce::File& destination)
{
    juce::ignoreUnused (tracks, bpm, destination);
    return false;
}

juce::File MidiExporter::writeExportFile (const cloud::JobResult& result, const juce::String& baseName)
{
    juce::ignoreUnused (result, baseName);
    return {};
}

juce::String MidiExporter::suggestedBaseName (const cloud::JobResult& result)
{
    return "snapplay_" + result.jobId.substring (0, 8);
}

} // namespace snapplay::exporting
