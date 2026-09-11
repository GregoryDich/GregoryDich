#include "TestFramework.h"

#include "Core/FscWriter.h"

#include <cstdint>
#include <string>
#include <vector>

namespace
{

using tonamorph::core::Note;
using tonamorph::core::Track;
using Bytes = std::vector<std::uint8_t>;

std::uint16_t readU16LE (const Bytes& bytes, std::size_t offset)
{
    return static_cast<std::uint16_t> (bytes.at (offset) | (bytes.at (offset + 1) << 8));
}

std::uint32_t readU32LE (const Bytes& bytes, std::size_t offset)
{
    return static_cast<std::uint32_t> (bytes.at (offset)) | (static_cast<std::uint32_t> (bytes.at (offset + 1)) << 8)
         | (static_cast<std::uint32_t> (bytes.at (offset + 2)) << 16) | (static_cast<std::uint32_t> (bytes.at (offset + 3)) << 24);
}

std::uint32_t readLeb128 (const Bytes& bytes, std::size_t& pos)
{
    std::uint32_t value = 0;
    int shift = 0;
    std::uint8_t byte = 0;

    do
    {
        byte = bytes.at (pos++);
        value |= static_cast<std::uint32_t> (byte & 0x7Fu) << shift;
        shift += 7;
    } while ((byte & 0x80u) != 0);

    return value;
}

Bytes varint (std::uint32_t value)
{
    Bytes out;
    tonamorph::core::detail::appendFlVarint (out, value);
    return out;
}

Note makeNote (double start, double duration, int pitch, int velocity = 100)
{
    Note note;
    note.startSeconds = start;
    note.durationSeconds = duration;
    note.pitch = pitch;
    note.velocity = velocity;
    return note;
}

constexpr std::size_t headerSize = 22;
constexpr std::size_t versionEventSize = 1 + 1 + 12;   // id, varint, "20.8.3.2304\0"

} // namespace

TONAMORPH_TEST(fscHeaderMatchesPyflpLayout)
{
    std::vector<Track> tracks (2);
    tracks[0].notes.push_back (makeNote (0.0, 0.5, 36));

    const Bytes bytes = tonamorph::core::writeFsc (tracks, 120.0);

    TONAMORPH_CHECK (std::string (bytes.begin(), bytes.begin() + 4) == "FLhd");
    TONAMORPH_CHECK_EQ (readU32LE (bytes, 4), 6u);
    TONAMORPH_CHECK_EQ (readU16LE (bytes, 8), 0x10);   // FileFormat.Score
    TONAMORPH_CHECK_EQ (readU16LE (bytes, 10), 2);     // channel count
    TONAMORPH_CHECK_EQ (readU16LE (bytes, 12), 96);    // PPQ
    TONAMORPH_CHECK (std::string (bytes.begin() + 14, bytes.begin() + 18) == "FLdt");
    TONAMORPH_CHECK_EQ (readU32LE (bytes, 18), static_cast<std::uint32_t> (bytes.size() - headerSize));
}

TONAMORPH_TEST(fscVarintIsLeb128)
{
    TONAMORPH_CHECK (varint (0x00) == (Bytes { 0x00 }));
    TONAMORPH_CHECK (varint (0x7F) == (Bytes { 0x7F }));
    TONAMORPH_CHECK (varint (0x80) == (Bytes { 0x80, 0x01 }));
    TONAMORPH_CHECK (varint (0x3FFF) == (Bytes { 0xFF, 0x7F }));
    TONAMORPH_CHECK (varint (300) == (Bytes { 0xAC, 0x02 }));
}

TONAMORPH_TEST(fscEventFramingAndVersionText)
{
    Track track;
    track.notes.push_back (makeNote (0.0, 0.5, 36));
    track.notes.push_back (makeNote (0.5, 0.5, 38));
    track.notes.push_back (makeNote (1.0, 0.5, 40));

    const Bytes bytes = tonamorph::core::writeFsc ({ track }, 120.0);

    std::size_t pos = headerSize;
    TONAMORPH_CHECK_EQ (int (bytes.at (pos++)), 199);
    TONAMORPH_CHECK_EQ (readLeb128 (bytes, pos), 12u);
    TONAMORPH_CHECK (std::string (bytes.begin() + static_cast<std::ptrdiff_t> (pos),
                                 bytes.begin() + static_cast<std::ptrdiff_t> (pos) + 11) == "20.8.3.2304");
    TONAMORPH_CHECK_EQ (int (bytes.at (pos + 11)), 0);   // NUL terminator
    pos += 12;

    TONAMORPH_CHECK_EQ (int (bytes.at (pos++)), 224);
    TONAMORPH_CHECK_EQ (readLeb128 (bytes, pos), 3u * 24u);
    TONAMORPH_CHECK_EQ (pos + 3 * 24, bytes.size());
}

TONAMORPH_TEST(fscNoteRecordFieldOffsets)
{
    Track track;
    track.channel = 3;
    track.notes.push_back (makeNote (0.5, 0.25, 62, 99));

    const Bytes bytes = tonamorph::core::writeFsc ({ track }, 120.0);
    const std::size_t record = headerSize + versionEventSize + 2;   // notes id + one-byte varint
    TONAMORPH_CHECK_EQ (record + 24, bytes.size());

    TONAMORPH_CHECK_EQ (readU32LE (bytes, record + 0), 96u);        // position: 0.5 s at 120 BPM, PPQ 96
    TONAMORPH_CHECK_EQ (readU16LE (bytes, record + 4), 0x4000);     // flags
    TONAMORPH_CHECK_EQ (readU16LE (bytes, record + 6), 0);          // rack_channel
    TONAMORPH_CHECK_EQ (readU32LE (bytes, record + 8), 48u);        // length: 0.25 s
    TONAMORPH_CHECK_EQ (readU32LE (bytes, record + 12), 62u);       // key (pyflp key u16 + group u16 = 0)
    TONAMORPH_CHECK_EQ (int (bytes.at (record + 16)), 120);         // fine_pitch
    TONAMORPH_CHECK_EQ (int (bytes.at (record + 17)), 0);           // u1
    TONAMORPH_CHECK_EQ (int (bytes.at (record + 18)), 64);          // release
    TONAMORPH_CHECK_EQ (int (bytes.at (record + 19)), 3);           // midi_channel
    TONAMORPH_CHECK_EQ (int (bytes.at (record + 20)), 64);          // pan
    TONAMORPH_CHECK_EQ (int (bytes.at (record + 21)), 99);          // velocity
    TONAMORPH_CHECK_EQ (int (bytes.at (record + 22)), 128);         // mod_x
    TONAMORPH_CHECK_EQ (int (bytes.at (record + 23)), 128);         // mod_y
}

TONAMORPH_TEST(fscNotesOrderedByPositionAcrossTracks)
{
    std::vector<Track> tracks (2);
    tracks[0].notes.push_back (makeNote (1.0, 0.5, 36));
    tracks[0].notes.push_back (makeNote (0.5, 0.5, 37));   // same position as the track-1 note: track order wins
    tracks[1].channel = 1;
    tracks[1].notes.push_back (makeNote (0.5, 0.5, 60));

    const Bytes bytes = tonamorph::core::writeFsc (tracks, 120.0);
    const std::size_t first = headerSize + versionEventSize + 2;

    TONAMORPH_CHECK_EQ (readU32LE (bytes, first), 96u);
    TONAMORPH_CHECK_EQ (readU16LE (bytes, first + 6), 0);
    TONAMORPH_CHECK_EQ (readU32LE (bytes, first + 12), 37u);

    TONAMORPH_CHECK_EQ (readU32LE (bytes, first + 24), 96u);
    TONAMORPH_CHECK_EQ (readU16LE (bytes, first + 24 + 6), 1);
    TONAMORPH_CHECK_EQ (int (bytes.at (first + 24 + 19)), 1);

    TONAMORPH_CHECK_EQ (readU32LE (bytes, first + 48), 192u);
    TONAMORPH_CHECK_EQ (readU32LE (bytes, first + 48 + 12), 36u);
}

TONAMORPH_TEST(fscEmptyInputIsStillAValidScore)
{
    const Bytes bytes = tonamorph::core::writeFsc ({}, 120.0);

    TONAMORPH_CHECK_EQ (bytes.size(), headerSize + versionEventSize + 2);
    TONAMORPH_CHECK_EQ (readU16LE (bytes, 10), 0);
    TONAMORPH_CHECK_EQ (readU32LE (bytes, 18), static_cast<std::uint32_t> (versionEventSize + 2));
    TONAMORPH_CHECK_EQ (int (bytes.at (headerSize + versionEventSize)), 224);
    TONAMORPH_CHECK_EQ (int (bytes.at (headerSize + versionEventSize + 1)), 0);   // empty PatternNotes payload
}

TONAMORPH_TEST(fscClampsOutOfRangeValues)
{
    Track track;
    track.channel = 42;
    track.notes.push_back (makeNote (0.0, 0.0, 300, 0));

    const Bytes bytes = tonamorph::core::writeFsc ({ track }, -5.0, 0);
    const std::size_t record = headerSize + versionEventSize + 2;

    TONAMORPH_CHECK_EQ (readU16LE (bytes, 12), 1);                 // ppq clamped to 1
    TONAMORPH_CHECK_EQ (readU32LE (bytes, record + 8), 1u);        // length stretched to one tick
    TONAMORPH_CHECK_EQ (readU32LE (bytes, record + 12), 127u);
    TONAMORPH_CHECK_EQ (int (bytes.at (record + 19)), 15);
    TONAMORPH_CHECK_EQ (int (bytes.at (record + 21)), 1);
}
