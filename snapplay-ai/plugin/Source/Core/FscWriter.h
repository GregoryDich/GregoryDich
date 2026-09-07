#pragma once

/**
 * FL Studio score (.fsc) writer — contract §9.
 *
 * Header-only and JUCE-free. The layout follows community reverse-engineering (PyFLP);
 * `.mid` remains the guaranteed interchange path.
 *
 * Byte layout matched against PyFLP 2.2.1 (the installed package):
 *  - `pyflp.__init__.FLP_HEADER = struct.Struct("4sIh2H")` (14 bytes, native little-endian,
 *    no padding): magic "FLhd", u32 header size 6, i16 format, u16 channel count, u16 ppq;
 *    `parse()` then expects "FLdt", a u32 event-stream size and `file size == size + 22`.
 *  - `pyflp.project.FileFormat.Score = 0x10`; `VALID_PPQS` includes 96.
 *  - `pyflp._events.EventBase.__bytes__`: one id byte, then for ids >= TEXT (192) a
 *    `construct.VarInt` length (LEB128: little-endian 7-bit groups, bit 7 set on every byte
 *    but the last) followed by the payload.
 *  - `pyflp.project.ProjectID.FLVersion = TEXT + 7 = 199`, typed `AsciiEvent`: the version
 *    text plus a trailing NUL (`AsciiEvent` builds `value + "\0"`); it is always ASCII, even
 *    though other text events switch to UTF-16 for versions >= 11.5.
 *  - `pyflp.pattern.PatternID.Notes = DATA + 16 = 224`, typed `NotesEvent`, whose
 *    `construct` STRUCT is a `GreedyRange` of 24-byte records: position Int32ul, flags
 *    Int16ul, rack_channel Int16ul, length Int32ul, key Int16ul, group Int16ul, fine_pitch
 *    Int8ul, _u1 Byte, release Int8ul, midi_channel Int8ul, pan Int8ul, velocity Int8ul,
 *    mod_x Int8ul, mod_y Int8ul. The contract's `key u32` is PyFLP's `key u16` followed by
 *    `group u16` = 0 (ungrouped), so the bytes are identical.
 *  - Field defaults from `pyflp.pattern.Note`: fine_pitch 120 (no fine tuning), release 64,
 *    pan 64 (centred), mod_x / mod_y 128. PyFLP's `_NoteFlags` only names bit 3 (Slide);
 *    0x4000 is the value FL Studio writes for plain notes.
 */

#include "Types.h"

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <limits>
#include <vector>

namespace snapplay::core
{

/** Size in bytes of one PatternNotes record (contract §9). */
inline constexpr int fscNoteRecordSize = 24;

/** FL Studio version written to the id-199 text event. */
inline constexpr char fscVersionText[] = "20.8.3.2304";

/** Event ids used by the score file (PyFLP `ProjectID.FLVersion`, `PatternID.Notes`). */
inline constexpr std::uint8_t fscVersionEventId = 199;
inline constexpr std::uint8_t fscNotesEventId = 224;

namespace detail
{

inline void appendU16LE (std::vector<std::uint8_t>& out, std::uint16_t value)
{
    out.push_back (static_cast<std::uint8_t> (value & 0xFFu));
    out.push_back (static_cast<std::uint8_t> (value >> 8));
}

inline void appendU32LE (std::vector<std::uint8_t>& out, std::uint32_t value)
{
    for (int shift = 0; shift <= 24; shift += 8)
        out.push_back (static_cast<std::uint8_t> ((value >> shift) & 0xFFu));
}

/** `construct.VarInt` (LEB128): little-endian 7-bit groups, bit 7 set on every byte but the last. */
inline void appendFlVarint (std::vector<std::uint8_t>& out, std::uint32_t value)
{
    do
    {
        auto byte = static_cast<std::uint8_t> (value & 0x7Fu);
        value >>= 7;

        if (value != 0)
            byte = static_cast<std::uint8_t> (byte | 0x80u);

        out.push_back (byte);
    } while (value != 0);
}

/** A data event (id >= 192): id byte, VarInt payload length, payload. */
inline void appendFlDataEvent (std::vector<std::uint8_t>& out, std::uint8_t id, const std::vector<std::uint8_t>& payload)
{
    out.push_back (id);
    appendFlVarint (out, static_cast<std::uint32_t> (payload.size()));
    out.insert (out.end(), payload.begin(), payload.end());
}

struct FscNoteRecord
{
    std::uint32_t position;
    std::uint32_t length;
    std::uint16_t rackChannel;
    std::uint8_t key;
    std::uint8_t midiChannel;
    std::uint8_t velocity;
};

inline void appendFscNoteRecord (std::vector<std::uint8_t>& out, const FscNoteRecord& record)
{
    appendU32LE (out, record.position);
    appendU16LE (out, 0x4000);              // flags
    appendU16LE (out, record.rackChannel);
    appendU32LE (out, record.length);
    appendU16LE (out, record.key);          // PyFLP "key" (low half of the contract's u32 key)
    appendU16LE (out, 0);                   // PyFLP "group": ungrouped
    out.push_back (120);                    // fine_pitch: centre
    out.push_back (0);                      // _u1
    out.push_back (64);                     // release
    out.push_back (record.midiChannel);
    out.push_back (64);                     // pan: centre
    out.push_back (record.velocity);
    out.push_back (128);                    // mod_x
    out.push_back (128);                    // mod_y
}

} // namespace detail

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
 * `ticks = round (seconds * bpm / 60 * ppq)`; the SMF tick fields are not read. Lengths
 * shorter than one tick are stretched to one tick (a zero length is a step-sequencer note
 * in FL Studio). Pitches are clamped to 0..127, velocities to 1..127, channels to 0..15.
 *
 * @param tracks  one entry per transcribed stem; each becomes one rack channel.
 * @param bpm     tempo from `analysis.bpm`; values <= 0 fall back to 120.
 * @param ppq     pulses per quarter note (contract: 96), clamped to 1..65535.
 * @return        the file bytes; never empty.
 */
inline std::vector<std::uint8_t> writeFsc (const std::vector<Track>& tracks, double bpm, int ppq = 96)
{
    using namespace detail;

    const double tempo = (std::isfinite (bpm) && bpm > 0.0) ? bpm : 120.0;
    const int flPpq = std::clamp (ppq, 1, 0xFFFF);
    const auto channelCount = static_cast<std::uint16_t> (std::min<std::size_t> (tracks.size(), 0xFFFF));

    std::vector<FscNoteRecord> records;
    for (std::size_t trackIndex = 0; trackIndex < channelCount; ++trackIndex)
    {
        const Track& track = tracks[trackIndex];
        const auto midiChannel = static_cast<std::uint8_t> (std::clamp (track.channel, 0, 15));

        for (const Note& note : track.notes)
        {
            records.push_back ({ static_cast<std::uint32_t> (secondsToTicks (note.startSeconds, tempo, flPpq)),
                                 static_cast<std::uint32_t> (std::max (1, secondsToTicks (note.durationSeconds, tempo, flPpq))),
                                 static_cast<std::uint16_t> (trackIndex),
                                 static_cast<std::uint8_t> (std::clamp (note.pitch, 0, 127)),
                                 midiChannel,
                                 static_cast<std::uint8_t> (std::clamp (note.velocity, 1, 127)) });
        }
    }

    std::stable_sort (records.begin(), records.end(), [] (const FscNoteRecord& a, const FscNoteRecord& b)
    {
        return a.position < b.position;
    });

    std::vector<std::uint8_t> version;                       // the version text and its NUL terminator
    version.reserve (sizeof (fscVersionText));
    for (const char character : fscVersionText)
        version.push_back (static_cast<std::uint8_t> (character));

    std::vector<std::uint8_t> notes;
    notes.reserve (records.size() * static_cast<std::size_t> (fscNoteRecordSize));
    for (const FscNoteRecord& record : records)
        appendFscNoteRecord (notes, record);

    std::vector<std::uint8_t> events;
    appendFlDataEvent (events, fscVersionEventId, version);
    appendFlDataEvent (events, fscNotesEventId, notes);

    std::vector<std::uint8_t> out;
    out.reserve (22 + events.size());
    out.insert (out.end(), { 'F', 'L', 'h', 'd' });
    appendU32LE (out, 6);
    appendU16LE (out, 0x10);
    appendU16LE (out, channelCount);
    appendU16LE (out, static_cast<std::uint16_t> (flPpq));
    out.insert (out.end(), { 'F', 'L', 'd', 't' });
    appendU32LE (out, static_cast<std::uint32_t> (events.size()));
    out.insert (out.end(), events.begin(), events.end());

    return out;
}

} // namespace snapplay::core
