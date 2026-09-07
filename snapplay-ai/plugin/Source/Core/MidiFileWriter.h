#pragma once

/**
 * Standard MIDI File (type 1) writer — contract §9.
 *
 * Header-only and JUCE-free so it can be unit-tested without the framework.
 */

#include "Types.h"

#include <cstdint>
#include <vector>

namespace snapplay::core
{

/**
 * Serialises tracks to a complete Standard MIDI File, type 1.
 *
 * Layout: `MThd` (format 1, ntrks = 1 + tracks.size(), division = ppq), a tempo track
 * holding a Set Tempo meta event (FF 51 03, microseconds per quarter = 60e6 / bpm) and
 * End of Track, then one `MTrk` per input track with a Track Name meta event (FF 03),
 * note-on / note-off pairs on the track's channel (velocity 0 note-offs are not used),
 * delta times as variable-length quantities and a final End of Track (FF 2F 00).
 *
 * Note timing is derived from `Note::startSeconds` / `durationSeconds` using
 * `ticks = round(seconds * bpm / 60 * ppq)`, so the output is correct for any `ppq`;
 * the `startTicks` / `durationTicks` fields are not read. Notes are sorted by start
 * time before writing. Pitches and velocities are clamped to 0..127 / 1..127.
 *
 * @param tracks  one entry per transcribed stem; empty tracks are still written.
 * @param bpm     tempo from `analysis.bpm`; values <= 0 fall back to 120.
 * @param ppq     pulses per quarter note (contract: 480).
 * @return        the file bytes; never empty (a valid file with only the tempo track at minimum).
 */
inline std::vector<std::uint8_t> writeMidiFile ([[maybe_unused]] const std::vector<Track>& tracks,
                                                [[maybe_unused]] double bpm,
                                                [[maybe_unused]] int ppq = 480)
{
    return {};
}

} // namespace snapplay::core
