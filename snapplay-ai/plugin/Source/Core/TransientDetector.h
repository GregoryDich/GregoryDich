#pragma once

/**
 * Client-side transient detection and slicing for drum mode (contract §8: when the server
 * reports no `slices`, slice locally from `transients_seconds`, or detect transients here).
 *
 * Header-only and JUCE-free.
 */

#include "Types.h"

#include <vector>

namespace snapplay::core
{

/**
 * Detects transient onsets in a mono signal.
 *
 * Spectral-flux-free energy method: 5 ms hops, per-hop RMS in dB, an onset is a hop whose
 * level rises >= 6 dB above the running 50 ms average and exceeds -40 dBFS, with a 50 ms
 * refractory period between onsets. The first onset is reported at the hop start.
 *
 * @return onset times in seconds, strictly increasing; empty for silent input.
 */
inline std::vector<double> detectTransients ([[maybe_unused]] const float* mono,
                                             [[maybe_unused]] int numSamples,
                                             [[maybe_unused]] double sampleRate)
{
    return {};
}

/**
 * Turns onset times into contiguous slices, each ending where the next begins (the last
 * one ends at `durationSeconds`), mapped to consecutive MIDI notes from `firstMidiNote`.
 *
 * Onsets outside [0, durationSeconds) are dropped; if the first onset is later than 0 the
 * region before it is not sliced. Never produces more than 128 - firstMidiNote slices.
 *
 * @return slices ordered by start time; empty when `transientsSeconds` is empty.
 */
inline std::vector<Slice> slicesFromTransients ([[maybe_unused]] const std::vector<double>& transientsSeconds,
                                                [[maybe_unused]] double durationSeconds,
                                                [[maybe_unused]] int firstMidiNote = 36)
{
    return {};
}

} // namespace snapplay::core
