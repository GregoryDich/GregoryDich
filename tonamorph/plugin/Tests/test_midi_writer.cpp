#include "TestFramework.h"

#include "Core/MidiFileWriter.h"

#include <cmath>
#include <cstdint>
#include <string>
#include <vector>

namespace
{

using tonamorph::core::Note;
using tonamorph::core::Track;
using Bytes = std::vector<std::uint8_t>;

std::uint32_t readU32BE (const Bytes& bytes, std::size_t offset)
{
    return (static_cast<std::uint32_t> (bytes.at (offset)) << 24) | (static_cast<std::uint32_t> (bytes.at (offset + 1)) << 16)
         | (static_cast<std::uint32_t> (bytes.at (offset + 2)) << 8) | static_cast<std::uint32_t> (bytes.at (offset + 3));
}

std::uint16_t readU16BE (const Bytes& bytes, std::size_t offset)
{
    return static_cast<std::uint16_t> ((bytes.at (offset) << 8) | bytes.at (offset + 1));
}

std::uint32_t readVlq (const Bytes& bytes, std::size_t& pos)
{
    std::uint32_t value = 0;
    std::uint8_t byte = 0;

    do
    {
        byte = bytes.at (pos++);
        value = (value << 7) | (byte & 0x7Fu);
    } while ((byte & 0x80u) != 0);

    return value;
}

struct ParsedEvent
{
    std::uint32_t tick = 0;
    std::uint8_t status = 0;     ///< channel status byte, or 0xFF for meta events
    std::uint8_t metaType = 0;
    Bytes data;
};

struct ParsedTrack
{
    std::vector<ParsedEvent> events;
    std::size_t chunkStart = 0;
    std::size_t chunkEnd = 0;    ///< offset just past the chunk
};

/** Minimal SMF track reader: no running status is expected in the writer's output. */
ParsedTrack parseTrack (const Bytes& bytes, std::size_t offset)
{
    ParsedTrack track;
    track.chunkStart = offset;

    TONAMORPH_CHECK (std::string (bytes.begin() + static_cast<std::ptrdiff_t> (offset),
                                 bytes.begin() + static_cast<std::ptrdiff_t> (offset) + 4) == "MTrk");

    const std::uint32_t length = readU32BE (bytes, offset + 4);
    std::size_t pos = offset + 8;
    track.chunkEnd = pos + length;
    std::uint32_t tick = 0;

    while (pos < track.chunkEnd)
    {
        tick += readVlq (bytes, pos);
        ParsedEvent event;
        event.tick = tick;
        event.status = bytes.at (pos++);

        if (event.status == 0xFF)
        {
            event.metaType = bytes.at (pos++);
            const std::uint32_t metaLength = readVlq (bytes, pos);
            event.data.assign (bytes.begin() + static_cast<std::ptrdiff_t> (pos),
                               bytes.begin() + static_cast<std::ptrdiff_t> (pos + metaLength));
            pos += metaLength;
        }
        else
        {
            TONAMORPH_CHECK (event.status >= 0x80);
            const int dataBytes = ((event.status & 0xF0) == 0xC0 || (event.status & 0xF0) == 0xD0) ? 1 : 2;
            for (int i = 0; i < dataBytes; ++i)
                event.data.push_back (bytes.at (pos++));
        }

        track.events.push_back (event);
    }

    TONAMORPH_CHECK_EQ (pos, track.chunkEnd);
    return track;
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

Bytes vlq (std::uint32_t value)
{
    Bytes out;
    tonamorph::core::detail::appendSmfVlq (out, value);
    return out;
}

} // namespace

TONAMORPH_TEST(midiHeaderFieldsMatchContract)
{
    std::vector<Track> tracks (2);
    tracks[0].name = "bass";
    tracks[1].name = "other";

    const Bytes bytes = tonamorph::core::writeMidiFile (tracks, 120.0);

    TONAMORPH_CHECK (bytes.size() > 14);
    TONAMORPH_CHECK (std::string (bytes.begin(), bytes.begin() + 4) == "MThd");
    TONAMORPH_CHECK_EQ (readU32BE (bytes, 4), 6u);
    TONAMORPH_CHECK_EQ (readU16BE (bytes, 8), 1);      // format 1
    TONAMORPH_CHECK_EQ (readU16BE (bytes, 10), 3);     // tempo track + 2 stems
    TONAMORPH_CHECK_EQ (readU16BE (bytes, 12), 480);   // PPQ
}

TONAMORPH_TEST(midiTempoTrackHoldsTempoAndTimeSignature)
{
    const Bytes bytes = tonamorph::core::writeMidiFile ({}, 120.0);
    TONAMORPH_CHECK_EQ (readU16BE (bytes, 10), 1);

    const ParsedTrack tempoTrack = parseTrack (bytes, 14);
    TONAMORPH_CHECK_EQ (tempoTrack.events.size(), 3u);
    TONAMORPH_CHECK_EQ (tempoTrack.chunkEnd, bytes.size());

    TONAMORPH_CHECK_EQ (tempoTrack.events[0].tick, 0u);
    TONAMORPH_CHECK_EQ (int (tempoTrack.events[0].metaType), 0x51);
    TONAMORPH_CHECK (tempoTrack.events[0].data == (Bytes { 0x07, 0xA1, 0x20 }));   // 500000 us = 120 BPM

    TONAMORPH_CHECK_EQ (int (tempoTrack.events[1].metaType), 0x58);
    TONAMORPH_CHECK (tempoTrack.events[1].data == (Bytes { 0x04, 0x02, 0x18, 0x08 }));

    TONAMORPH_CHECK_EQ (int (tempoTrack.events[2].metaType), 0x2F);
    TONAMORPH_CHECK (tempoTrack.events[2].data.empty());

    // Non-integer tempo rounds to the nearest microsecond.
    const Bytes at124 = tonamorph::core::writeMidiFile ({}, 124.0);
    const ParsedTrack track124 = parseTrack (at124, 14);
    const auto micros = std::lround (60'000'000.0 / 124.0);
    TONAMORPH_CHECK (track124.events[0].data == (Bytes { static_cast<std::uint8_t> (micros >> 16),
                                                        static_cast<std::uint8_t> ((micros >> 8) & 0xFF),
                                                        static_cast<std::uint8_t> (micros & 0xFF) }));

    // Invalid tempos fall back to 120 BPM.
    const Bytes fallback = tonamorph::core::writeMidiFile ({}, 0.0);
    TONAMORPH_CHECK (parseTrack (fallback, 14).events[0].data == (Bytes { 0x07, 0xA1, 0x20 }));
}

TONAMORPH_TEST(midiVariableLengthQuantities)
{
    TONAMORPH_CHECK (vlq (0x00) == (Bytes { 0x00 }));
    TONAMORPH_CHECK (vlq (0x7F) == (Bytes { 0x7F }));
    TONAMORPH_CHECK (vlq (0x80) == (Bytes { 0x81, 0x00 }));
    TONAMORPH_CHECK (vlq (0x3FFF) == (Bytes { 0xFF, 0x7F }));
    TONAMORPH_CHECK (vlq (0x4000) == (Bytes { 0x81, 0x80, 0x00 }));
    TONAMORPH_CHECK (vlq (0x0FFFFFFF) == (Bytes { 0xFF, 0xFF, 0xFF, 0x7F }));
}

TONAMORPH_TEST(midiTickMathFollowsTimingRule)
{
    using tonamorph::core::secondsToTicks;

    TONAMORPH_CHECK_EQ (secondsToTicks (0.5, 120.0, 480), 480);
    TONAMORPH_CHECK_EQ (secondsToTicks (1.0, 124.0, 480), 992);
    TONAMORPH_CHECK_EQ (secondsToTicks (0.25, 90.0, 96), 36);
    TONAMORPH_CHECK_EQ (secondsToTicks (-1.0, 120.0, 480), 0);
    TONAMORPH_CHECK_EQ (secondsToTicks (std::nan (""), 120.0, 480), 0);

    Track track;
    track.channel = 2;
    track.notes.push_back (makeNote (0.5, 0.25, 60, 90));

    // Tick fields win over seconds when the server filled them.
    Note fromTicks = makeNote (3.0, 3.0, 62);
    fromTicks.startTicks = 960;
    fromTicks.durationTicks = 496;
    track.notes.push_back (fromTicks);

    const ParsedTrack parsed = parseTrack (tonamorph::core::writeMidiFile ({ track }, 120.0), 14 + 8 + 19);
    TONAMORPH_CHECK_EQ (parsed.events.size(), 6u);   // name, 2 x (on, off), end of track

    TONAMORPH_CHECK_EQ (int (parsed.events[0].metaType), 0x03);
    TONAMORPH_CHECK_EQ (parsed.events[1].tick, 480u);
    TONAMORPH_CHECK_EQ (int (parsed.events[1].status), 0x92);
    TONAMORPH_CHECK (parsed.events[1].data == (Bytes { 60, 90 }));
    TONAMORPH_CHECK_EQ (parsed.events[2].tick, 720u);
    TONAMORPH_CHECK_EQ (int (parsed.events[2].status), 0x82);
    TONAMORPH_CHECK (parsed.events[2].data == (Bytes { 60, 64 }));
    TONAMORPH_CHECK_EQ (parsed.events[3].tick, 960u);
    TONAMORPH_CHECK (parsed.events[3].data == (Bytes { 62, 100 }));
    TONAMORPH_CHECK_EQ (parsed.events[4].tick, 1456u);

    // Tick fields are rescaled when the file uses a different PPQ than the server's 480.
    const ParsedTrack at96 = parseTrack (tonamorph::core::writeMidiFile ({ track }, 120.0, 96), 14 + 8 + 19);
    TONAMORPH_CHECK_EQ (at96.events[1].tick, 96u);
    TONAMORPH_CHECK_EQ (at96.events[2].tick, 144u);
    TONAMORPH_CHECK_EQ (at96.events[3].tick, 192u);
    TONAMORPH_CHECK_EQ (at96.events[4].tick, 291u);   // 192 + round (496 * 96 / 480)
}

TONAMORPH_TEST(midiNoteOffPrecedesNoteOnAtEqualTicks)
{
    Track track;
    // Deliberately unsorted: the retrigger comes first in the input.
    track.notes.push_back (makeNote (0.5, 0.5, 60));
    track.notes.push_back (makeNote (0.0, 0.5, 60));

    const ParsedTrack parsed = parseTrack (tonamorph::core::writeMidiFile ({ track }, 120.0), 14 + 8 + 19);
    TONAMORPH_CHECK_EQ (parsed.events.size(), 6u);

    TONAMORPH_CHECK_EQ (parsed.events[1].tick, 0u);
    TONAMORPH_CHECK_EQ (int (parsed.events[1].status), 0x90);
    TONAMORPH_CHECK_EQ (parsed.events[2].tick, 480u);
    TONAMORPH_CHECK_EQ (int (parsed.events[2].status), 0x80);   // off before the retrigger
    TONAMORPH_CHECK_EQ (parsed.events[3].tick, 480u);
    TONAMORPH_CHECK_EQ (int (parsed.events[3].status), 0x90);
    TONAMORPH_CHECK_EQ (parsed.events[4].tick, 960u);
    TONAMORPH_CHECK_EQ (int (parsed.events[4].status), 0x80);
}

TONAMORPH_TEST(midiEveryTrackEndsWithEndOfTrack)
{
    std::vector<Track> tracks (3);
    tracks[0].name = "bass";
    tracks[0].notes.push_back (makeNote (0.0, 1.0, 40));
    tracks[1].name = "drums";   // empty tracks are still written
    tracks[2].name = "other";
    tracks[2].channel = 1;
    tracks[2].notes.push_back (makeNote (2.0, 0.5, 72));

    const Bytes bytes = tonamorph::core::writeMidiFile (tracks, 100.0);
    TONAMORPH_CHECK_EQ (readU16BE (bytes, 10), 4);

    std::size_t offset = 14;
    for (int i = 0; i < 4; ++i)
    {
        const ParsedTrack parsed = parseTrack (bytes, offset);
        TONAMORPH_CHECK (! parsed.events.empty());
        TONAMORPH_CHECK_EQ (int (parsed.events.back().status), 0xFF);
        TONAMORPH_CHECK_EQ (int (parsed.events.back().metaType), 0x2F);
        TONAMORPH_CHECK (bytes.at (parsed.chunkEnd - 4) == 0x00 && bytes.at (parsed.chunkEnd - 3) == 0xFF
                        && bytes.at (parsed.chunkEnd - 2) == 0x2F && bytes.at (parsed.chunkEnd - 1) == 0x00);

        if (i > 0)
        {
            TONAMORPH_CHECK_EQ (int (parsed.events[0].metaType), 0x03);
            TONAMORPH_CHECK (std::string (parsed.events[0].data.begin(), parsed.events[0].data.end()) == tracks[static_cast<std::size_t> (i - 1)].name);
        }

        offset = parsed.chunkEnd;
    }

    TONAMORPH_CHECK_EQ (offset, bytes.size());
}

TONAMORPH_TEST(midiClampsOutOfRangeValues)
{
    Track track;
    track.channel = 20;
    track.notes.push_back (makeNote (0.0, 0.0, 200, 0));   // zero duration, pitch and velocity out of range

    const ParsedTrack parsed = parseTrack (tonamorph::core::writeMidiFile ({ track }, 120.0), 14 + 8 + 19);
    TONAMORPH_CHECK_EQ (parsed.events.size(), 4u);
    TONAMORPH_CHECK_EQ (int (parsed.events[1].status), 0x9F);
    TONAMORPH_CHECK (parsed.events[1].data == (Bytes { 127, 1 }));
    TONAMORPH_CHECK_EQ (parsed.events[2].tick, 1u);   // stretched to one tick so the pair survives
}
