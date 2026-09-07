#pragma once

/**
 * Standard MIDI File (type 1) writer — contract §9.
 *
 * Header-only and JUCE-free so it can be unit-tested without the framework.
 */

#include "Types.h"

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <utility>
#include <vector>

namespace snapplay::core
{

namespace detail
{

/** PPQ at which `Note::startTicks` / `durationTicks` are expressed (Types.h: the server's 480). */
inline constexpr int noteFieldPpq = 480;

/** Largest value a four-byte SMF variable-length quantity can hold. */
inline constexpr std::int64_t maxSmfVlq = 0x0FFFFFFF;

inline void appendU16BE (std::vector<std::uint8_t>& out, std::uint16_t value)
{
    out.push_back (static_cast<std::uint8_t> (value >> 8));
    out.push_back (static_cast<std::uint8_t> (value & 0xFFu));
}

inline void appendU32BE (std::vector<std::uint8_t>& out, std::uint32_t value)
{
    for (int shift = 24; shift >= 0; shift -= 8)
        out.push_back (static_cast<std::uint8_t> ((value >> shift) & 0xFFu));
}

/** SMF variable-length quantity: big-endian 7-bit groups, bit 7 set on every byte but the last. */
inline void appendSmfVlq (std::vector<std::uint8_t>& out, std::uint32_t value)
{
    std::uint8_t groups[5];
    int count = 0;

    do
    {
        groups[count++] = static_cast<std::uint8_t> (value & 0x7Fu);
        value >>= 7;
    } while (value != 0);

    for (int i = count - 1; i >= 0; --i)
        out.push_back (static_cast<std::uint8_t> (i > 0 ? (groups[i] | 0x80u) : groups[i]));
}

/** Prefixes `events` with an `MTrk` header and appends the chunk to `out`. */
inline void appendTrackChunk (std::vector<std::uint8_t>& out, const std::vector<std::uint8_t>& events)
{
    out.insert (out.end(), { 'M', 'T', 'r', 'k' });
    appendU32BE (out, static_cast<std::uint32_t> (events.size()));
    out.insert (out.end(), events.begin(), events.end());
}

inline void appendEndOfTrack (std::vector<std::uint8_t>& events)
{
    events.insert (events.end(), { 0x00, 0xFF, 0x2F, 0x00 });
}

/**
 * Start / duration of a note in ticks at `ppq`. The tick fields win when the server filled
 * them (`durationTicks > 0`), rescaled from `noteFieldPpq` if `ppq` differs; otherwise the
 * seconds are converted with the contract timing rule.
 */
inline std::pair<std::int64_t, std::int64_t> noteTicks (const Note& note, double bpm, int ppq) noexcept
{
    if (note.durationTicks > 0)
    {
        const std::int64_t start = std::max (0, note.startTicks);

        if (ppq == noteFieldPpq)
            return { start, note.durationTicks };

        const double scale = static_cast<double> (ppq) / static_cast<double> (noteFieldPpq);
        return { std::llround (static_cast<double> (start) * scale),
                 std::max<std::int64_t> (1, std::llround (static_cast<double> (note.durationTicks) * scale)) };
    }

    return { secondsToTicks (note.startSeconds, bpm, ppq),
             secondsToTicks (note.durationSeconds, bpm, ppq) };
}

struct SmfChannelEvent
{
    std::int64_t tick;
    int order;              ///< 0 = note-off, 1 = note-on: at equal ticks the off is written first
    std::uint8_t status;
    std::uint8_t data1;
    std::uint8_t data2;
};

} // namespace detail

/**
 * Serialises tracks to a complete Standard MIDI File, type 1.
 *
 * Layout: `MThd` (format 1, ntrks = 1 + tracks.size(), division = ppq), a tempo track
 * holding a Set Tempo meta event (FF 51 03, microseconds per quarter = round (60e6 / bpm)),
 * a 4/4 Time Signature meta event (FF 58 04 04 02 18 08) and End of Track, then one `MTrk`
 * per input track with a Track Name meta event (FF 03), note-on / note-off pairs on the
 * track's channel (real 8n note-offs with release velocity 64; running status is not
 * used), delta times as variable-length quantities and a final End of Track (FF 2F 00).
 *
 * Timing: a note whose `durationTicks` is set (> 0) uses `startTicks` / `durationTicks`
 * (rescaled from the server's 480 PPQ when `ppq` differs); otherwise
 * `ticks = round (seconds * bpm / 60 * ppq)` from `startSeconds` / `durationSeconds`.
 * Durations shorter than one tick are stretched to one tick. Events are sorted by tick with
 * note-offs before note-ons at equal ticks so retriggered pitches keep their pairing.
 * Pitches are clamped to 0..127, velocities to 1..127, channels to 0..15.
 *
 * @param tracks  one entry per transcribed stem; empty tracks are still written.
 * @param bpm     tempo from `analysis.bpm`; values <= 0 fall back to 120.
 * @param ppq     pulses per quarter note (contract: 480), clamped to 1..32767.
 * @return        the file bytes; never empty (a valid file with only the tempo track at minimum).
 */
inline std::vector<std::uint8_t> writeMidiFile (const std::vector<Track>& tracks, double bpm, int ppq = 480)
{
    using namespace detail;

    const double tempo = (std::isfinite (bpm) && bpm > 0.0) ? bpm : 120.0;
    const int division = std::clamp (ppq, 1, 0x7FFF);
    const auto microsPerQuarter = static_cast<std::uint32_t> (
        std::clamp<long> (std::lround (60'000'000.0 / tempo), 1L, 0xFFFFFFL));
    const auto numTracks = static_cast<std::uint16_t> (std::min<std::size_t> (tracks.size(), 0xFFFE) + 1);

    std::vector<std::uint8_t> out;
    out.insert (out.end(), { 'M', 'T', 'h', 'd' });
    appendU32BE (out, 6);
    appendU16BE (out, 1);
    appendU16BE (out, numTracks);
    appendU16BE (out, static_cast<std::uint16_t> (division));

    {
        std::vector<std::uint8_t> tempoTrack;
        tempoTrack.insert (tempoTrack.end(), { 0x00, 0xFF, 0x51, 0x03,
                                               static_cast<std::uint8_t> ((microsPerQuarter >> 16) & 0xFFu),
                                               static_cast<std::uint8_t> ((microsPerQuarter >> 8) & 0xFFu),
                                               static_cast<std::uint8_t> (microsPerQuarter & 0xFFu) });
        tempoTrack.insert (tempoTrack.end(), { 0x00, 0xFF, 0x58, 0x04, 0x04, 0x02, 0x18, 0x08 });
        appendEndOfTrack (tempoTrack);
        appendTrackChunk (out, tempoTrack);
    }

    for (std::size_t trackIndex = 0; trackIndex + 1 < numTracks; ++trackIndex)
    {
        const Track& track = tracks[trackIndex];
        const auto channel = static_cast<std::uint8_t> (std::clamp (track.channel, 0, 15));

        std::vector<std::uint8_t> chunk;
        chunk.insert (chunk.end(), { 0x00, 0xFF, 0x03 });
        const auto nameLength = static_cast<std::uint32_t> (std::min<std::size_t> (track.name.size(), maxSmfVlq));
        appendSmfVlq (chunk, nameLength);
        for (std::uint32_t i = 0; i < nameLength; ++i)
            chunk.push_back (static_cast<std::uint8_t> (track.name[i]));

        std::vector<SmfChannelEvent> events;
        events.reserve (track.notes.size() * 2);

        for (const Note& note : track.notes)
        {
            const auto [rawStart, rawDuration] = noteTicks (note, tempo, division);
            const std::int64_t start = std::clamp<std::int64_t> (rawStart, 0, maxSmfVlq - 1);
            const std::int64_t end = std::clamp<std::int64_t> (start + std::max<std::int64_t> (1, rawDuration),
                                                               start + 1, maxSmfVlq);
            const auto pitch = static_cast<std::uint8_t> (std::clamp (note.pitch, 0, 127));
            const auto velocity = static_cast<std::uint8_t> (std::clamp (note.velocity, 1, 127));

            events.push_back ({ start, 1, static_cast<std::uint8_t> (0x90u | channel), pitch, velocity });
            events.push_back ({ end, 0, static_cast<std::uint8_t> (0x80u | channel), pitch, 64 });
        }

        std::stable_sort (events.begin(), events.end(), [] (const SmfChannelEvent& a, const SmfChannelEvent& b)
        {
            return a.tick != b.tick ? a.tick < b.tick : a.order < b.order;
        });

        std::int64_t lastTick = 0;
        for (const SmfChannelEvent& event : events)
        {
            appendSmfVlq (chunk, static_cast<std::uint32_t> (event.tick - lastTick));
            chunk.push_back (event.status);
            chunk.push_back (event.data1);
            chunk.push_back (event.data2);
            lastTick = event.tick;
        }

        appendEndOfTrack (chunk);
        appendTrackChunk (out, chunk);
    }

    return out;
}

} // namespace snapplay::core
