#pragma once

/**
 * `.fsc` export (contract §9): FL Studio score file at PPQ 96. Serialisation is
 * core::writeFsc; this class adds the JUCE file plumbing.
 */

#include <JuceHeader.h>

#include "Cloud/Models.h"
#include "Core/Types.h"

#include <vector>

namespace snapplay::exporting
{

class FscExporter
{
public:
    static constexpr int ppq = 96;
    static constexpr const char* extension = ".fsc";

    /** File bytes for the given tracks and tempo. */
    static juce::MemoryBlock toMemoryBlock (const std::vector<core::Track>& tracks, double bpm);
    /** Writes `destination` (overwriting); false on I/O failure. */
    static bool writeToFile (const std::vector<core::Track>& tracks, double bpm, const juce::File& destination);
    /** Writes `<DragExport::exportDirectory()>/<baseName>.fsc` from `result.midi.tracks`
        at `result.analysis.bpm`. Returns a File that does not exist on failure. */
    static juce::File writeExportFile (const cloud::JobResult& result, const juce::String& baseName);

private:
    FscExporter() = delete;
};

} // namespace snapplay::exporting
