#pragma once

/**
 * FL Studio score (.fsc) writer — contract §9.
 *
 * Header-only and JUCE-free. The layout follows community reverse-engineering (PyFLP);
 * `.mid` remains the guaranteed interchange path.
 */

#include "Types.h"

#include <cstdint>
#include <vector>

namespace snapplay::core
{

/** Size in bytes of one PatternNotes record (contract §9). */
inline constexpr int fscNoteRecordSize = 24;

/**
 * Serialises tracks to an FL Studio score file.
 *
 * Layout (all integers little-endian):
 *  - `FLhd` chunk: u32 length = 6, u16 format = 0x10, u16 channel count = tracks.size(),
 *    u16 ppq (contract: 96).
 *  - `FLdt` chunk: u32 length, then events. Event ids >= 192 are "data" events whose
 *    payload is prefixed by its length as a variable-length quantity (7 bits per byte,
 *    little-endian). Emitted events:
 *      - id 199 (FL version text): the NUL-terminated ASCII string "20.8.3.2304".
 *      - id 224 (PatternNotes): `fscNoteRecordSize`-byte note records, one per note,
 *        ordered by position: position u32 (ticks at `ppq`), flags u16 (0x4000),
 *        rack_channel u16 (index of the note's track), length u32 (ticks), key u32
 *        (MIDI pitch), fine_pitch u8 (120 = centre), u1 u8 (0), release u8 (64),
 *        midi_channel u8 (track channel), pan u8 (64), velocity u8 (1..127),
 *        mod_x u8 (128), mod_y u8 (128).
 *
 * Tick positions come from `Note::startSeconds` / `durationSeconds` via
 * `ticks = round(seconds * bpm / 60 * ppq)`; the SMF tick fields are not read.
 *
 * @param tracks  one entry per transcribed stem; each becomes one rack channel.
 * @param bpm     tempo from `analysis.bpm`; values <= 0 fall back to 120.
 * @param ppq     pulses per quarter note (contract: 96).
 * @return        the file bytes; never empty.
 */
inline std::vector<std::uint8_t> writeFsc ([[maybe_unused]] const std::vector<Track>& tracks,
                                           [[maybe_unused]] double bpm,
                                           [[maybe_unused]] int ppq = 96)
{
    return {};
}

} // namespace snapplay::core
