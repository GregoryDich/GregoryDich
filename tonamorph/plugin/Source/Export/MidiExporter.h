#pragma once

/**
 * `.mid` export (contract §9): Standard MIDI File type 1 at PPQ 480, tempo from
 * `analysis.bpm`, one track per transcribed stem. Serialisation is core::writeMidiFile;
 * this class adds the JUCE file plumbing.
 */

#include <JuceHeader.h>

#include "Cloud/Models.h"
#include "Core/Types.h"

#include <vector>

namespace tonamorph::exporting
{

class MidiExporter
{
public:
    static constexpr int ppq = 480;
    static constexpr const char* extension = ".mid";

    /** File bytes for the given tracks and tempo. */
    static juce::MemoryBlock toMemoryBlock (const std::vector<core::Track>& tracks, double bpm);
    /** Writes `destination` (overwriting); false on I/O failure. */
    static bool writeToFile (const std::vector<core::Track>& tracks, double bpm, const juce::File& destination);
    /** Writes `<DragExport::exportDirectory()>/<baseName>.mid` from `result.midi.tracks`
        at `result.analysis.bpm`. Returns a File that does not exist on failure. */
    static juce::File writeExportFile (const cloud::JobResult& result, const juce::String& baseName);
    /** "tonamorph_<first 8 chars of the job id>" — the base name both exporters use. */
    static juce::String suggestedBaseName (const cloud::JobResult& result);

private:
    MidiExporter() = delete;
};

} // namespace tonamorph::exporting
