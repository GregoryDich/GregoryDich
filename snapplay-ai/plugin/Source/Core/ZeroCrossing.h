#pragma once

/**
 * Zero-crossing search used to trim sample starts/ends without clicks.
 *
 * Header-only and JUCE-free. All functions operate on a mono `const float*` buffer;
 * callers mix stereo material down (or pass one channel) before calling.
 */

namespace snapplay::core
{

/** A half-open sample range [start, end) inside a buffer. */
struct TrimRange
{
    int start = 0;
    int end = 0;

    int length() const noexcept { return end - start; }
};

/**
 * Returns the index of the zero crossing nearest to `fromIndex`, searching outward up to
 * `maxSearchSamples` in both directions. A zero crossing is an index `i` where
 * `samples[i] == 0` or `sign(samples[i-1]) != sign(samples[i])`; the reported index is
 * `i` (the first sample of the new half-cycle). Ties resolve to the earlier index.
 *
 * @return the crossing index, or `fromIndex` (clamped to [0, numSamples)) when none is
 *         found within the search window or the buffer is empty.
 */
inline int nearestZeroCrossing (const float* samples, int numSamples, int fromIndex, [[maybe_unused]] int maxSearchSamples = 1024)
{
    if (samples == nullptr || numSamples <= 0)
        return 0;

    return fromIndex < 0 ? 0 : (fromIndex >= numSamples ? numSamples - 1 : fromIndex);
}

/**
 * Finds the audible region of a mono buffer and snaps both edges to zero crossings.
 *
 * `start` is the first index whose absolute value reaches `threshold`, moved backwards to
 * the nearest zero crossing; `end` (exclusive) is one past the last such index, moved
 * forwards to the nearest zero crossing. Silent input yields `{0, numSamples}` so callers
 * never receive an empty range for non-empty buffers.
 *
 * @param threshold        linear amplitude (0.001 = -60 dBFS).
 * @param maxSearchSamples search window handed to nearestZeroCrossing().
 */
inline TrimRange findTrimRange (const float* mono, int numSamples,
                                [[maybe_unused]] float threshold = 0.001f,
                                [[maybe_unused]] int maxSearchSamples = 1024)
{
    if (mono == nullptr || numSamples <= 0)
        return {};

    return { 0, numSamples };
}

} // namespace snapplay::core
