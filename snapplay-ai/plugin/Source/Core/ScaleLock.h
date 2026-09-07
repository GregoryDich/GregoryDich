#pragma once

/**
 * Scale-Snap pitch quantiser (contract §8).
 *
 * Header-only and JUCE-free. `ScaleLock` is the message-thread model; the audio thread
 * uses the lock-free helpers `pitchClassMask()` / `snapToMask()` on a 12-bit mask.
 */

#include "Types.h"

#include <cstdint>
#include <utility>
#include <vector>

namespace snapplay::core
{

/** Wraps any integer into a pitch class 0..11 (negative inputs included). */
inline int toPitchClass (int value) noexcept
{
    return ((value % 12) + 12) % 12;
}

/**
 * Returns the pitch classes of the contract §8 table for a mode rotated to `rootPitchClass`.
 *
 * Major 0 2 4 5 7 9 11 · Minor 0 2 3 5 7 8 10 · PentatonicMajor 0 2 4 7 9 ·
 * PentatonicMinor 0 3 5 7 10. `Detected` and `Off` have no computed set and return an
 * empty vector (the detected set comes from `analysis.key.scale_pitch_classes`).
 * The result is sorted ascending.
 */
inline std::vector<int> pitchClassesFor (ScaleMode mode, int rootPitchClass)
{
    const int root = toPitchClass (rootPitchClass);
    std::vector<int> intervals;

    switch (mode)
    {
        case ScaleMode::Major:           intervals = { 0, 2, 4, 5, 7, 9, 11 }; break;
        case ScaleMode::Minor:           intervals = { 0, 2, 3, 5, 7, 8, 10 }; break;
        case ScaleMode::PentatonicMajor: intervals = { 0, 2, 4, 7, 9 };        break;
        case ScaleMode::PentatonicMinor: intervals = { 0, 3, 5, 7, 10 };       break;
        case ScaleMode::Detected:
        case ScaleMode::Off:             return {};
    }

    std::vector<int> result;
    result.reserve (intervals.size());

    for (const int interval : intervals)
        result.push_back (toPitchClass (root + interval));

    // Rotate into ascending order so callers can compare sets directly.
    for (std::size_t i = 1; i < result.size(); ++i)
        for (std::size_t j = i; j > 0 && result[j - 1] > result[j]; --j)
            std::swap (result[j - 1], result[j]);

    return result;
}

/** Packs pitch classes into a 12-bit mask (bit n set = pitch class n allowed). */
inline std::uint16_t pitchClassMask (const std::vector<int>& pitchClasses) noexcept
{
    std::uint16_t mask = 0;

    for (const int pitchClass : pitchClasses)
        mask = static_cast<std::uint16_t> (mask | (1u << static_cast<unsigned> (toPitchClass (pitchClass))));

    return mask;
}

/**
 * Snaps a MIDI note to the nearest pitch class allowed by `mask`.
 *
 * Ties resolve downward (contract §8). Candidates outside 0..127 are skipped. A mask with
 * no bits set means passthrough and returns `midiNote` unchanged. Lock-free and
 * allocation-free, safe on the audio thread.
 */
inline int snapToMask (int midiNote, std::uint16_t mask) noexcept
{
    if ((mask & 0x0FFFu) == 0)
        return midiNote;

    const auto allowed = [mask] (int note) noexcept
    {
        return (mask & (1u << static_cast<unsigned> (toPitchClass (note)))) != 0;
    };

    if (allowed (midiNote))
        return midiNote;

    for (int distance = 1; distance <= 6; ++distance)
    {
        const int below = midiNote - distance;
        if (below >= 0 && allowed (below))
            return below;

        const int above = midiNote + distance;
        if (above <= 127 && allowed (above))
            return above;
    }

    return midiNote;
}

/**
 * Message-thread model of the Scale-Snap state: the detected scale plus the selected mode
 * and root. Use getMask() to publish the active set to the audio thread atomically.
 */
class ScaleLock
{
public:
    ScaleLock() = default;

    /** Installs the detected pitch-class set (`analysis.key.scale_pitch_classes`).
        Used verbatim when the mode is Detected; ignored by the computed modes. */
    void setScale (std::vector<int> pitchClasses)
    {
        detected = std::move (pitchClasses);
        rebuild();
    }

    /** Selects the mode and root pitch class (0..11, wrapped). Detected ignores the root;
        Off disables snapping. */
    void setMode (ScaleMode newMode, int rootPitchClass)
    {
        mode = newMode;
        root = toPitchClass (rootPitchClass);
        rebuild();
    }

    /** Snaps `midiNote` to the active set (ties resolve downward); passthrough when off. */
    int snap (int midiNote) const noexcept { return snapToMask (midiNote, mask); }

    /** True when no snapping happens: mode Off, or Detected with no scale installed. */
    bool isPassthrough() const noexcept { return (mask & 0x0FFFu) == 0; }

    ScaleMode getMode() const noexcept { return mode; }
    int getRootPitchClass() const noexcept { return root; }

    /** The pitch classes currently used for snapping (empty when passthrough). */
    const std::vector<int>& getActivePitchClasses() const noexcept { return active; }

    /** The detected set installed with setScale() (may be empty). */
    const std::vector<int>& getDetectedPitchClasses() const noexcept { return detected; }

    /** 12-bit mask of the active set, suitable for a std::atomic<uint16_t> handoff. */
    std::uint16_t getMask() const noexcept { return mask; }

private:
    void rebuild()
    {
        active = mode == ScaleMode::Detected ? detected : pitchClassesFor (mode, root);
        mask = pitchClassMask (active);
    }

    std::vector<int> detected;
    std::vector<int> active;
    ScaleMode mode = ScaleMode::Detected;
    int root = 0;
    std::uint16_t mask = 0;
};

} // namespace snapplay::core
