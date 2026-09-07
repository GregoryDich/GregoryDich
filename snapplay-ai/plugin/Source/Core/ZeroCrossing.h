#pragma once

/**
 * Zero-crossing search used to trim sample starts/ends without clicks.
 *
 * Header-only and JUCE-free. All functions operate on a mono `const float*` buffer;
 * callers mix stereo material down (or pass one channel) before calling.
 */

#include <algorithm>
#include <cmath>

namespace snapplay::core
{

/** A half-open sample range [start, end) inside a buffer. */
struct TrimRange
{
    int start = 0;
    int end = 0;

    int length() const noexcept { return end - start; }
};

namespace detail
{

/** True when `index` starts a new half-cycle: the sample is zero or its sign differs from the previous one. */
inline bool isZeroCrossing (const float* samples, int index) noexcept
{
    if (samples[index] == 0.0f)
        return true;

    return index > 0 && ((samples[index - 1] < 0.0f) != (samples[index] < 0.0f));
}

/** Nearest crossing at or before `from` within `maxSearch` samples, or -1. */
inline int zeroCrossingBackward (const float* samples, int numSamples, int from, int maxSearch) noexcept
{
    const int lowest = std::max (0, from - maxSearch);

    for (int i = std::min (from, numSamples - 1); i >= lowest; --i)
        if (isZeroCrossing (samples, i))
            return i;

    return -1;
}

/** Nearest crossing at or after `from` within `maxSearch` samples, or -1. */
inline int zeroCrossingForward (const float* samples, int numSamples, int from, int maxSearch) noexcept
{
    const int highest = std::min (numSamples - 1, from + maxSearch);

    for (int i = std::max (from, 0); i <= highest; ++i)
        if (isZeroCrossing (samples, i))
            return i;

    return -1;
}

} // namespace detail

/**
 * Returns the index of the zero crossing nearest to `fromIndex`, searching outward up to
 * `maxSearchSamples` in both directions. A zero crossing is an index `i` where
 * `samples[i] == 0` or `sign(samples[i-1]) != sign(samples[i])`; the reported index is
 * `i` (the first sample of the new half-cycle). Ties resolve to the earlier index.
 *
 * @return the crossing index, or `fromIndex` (clamped to [0, numSamples)) when none is
 *         found within the search window or the buffer is empty.
 */
inline int nearestZeroCrossing (const float* samples, int numSamples, int fromIndex, int maxSearchSamples = 1024)
{
    if (samples == nullptr || numSamples <= 0)
        return 0;

    const int from = std::clamp (fromIndex, 0, numSamples - 1);
    const int window = std::max (0, maxSearchSamples);

    for (int distance = 0; distance <= window; ++distance)
    {
        const int earlier = from - distance;
        if (earlier >= 0 && detail::isZeroCrossing (samples, earlier))
            return earlier;

        const int later = from + distance;
        if (later < numSamples && detail::isZeroCrossing (samples, later))
            return later;

        if (earlier < 0 && later >= numSamples)
            break;
    }

    return from;
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
 * @param maxSearchSamples search window handed to the directional crossing search.
 */
inline TrimRange findTrimRange (const float* mono, int numSamples,
                                float threshold = 0.001f,
                                int maxSearchSamples = 1024)
{
    if (mono == nullptr || numSamples <= 0)
        return {};

    int first = -1;
    int last = -1;

    for (int i = 0; i < numSamples; ++i)
    {
        if (std::fabs (mono[i]) >= threshold)
        {
            if (first < 0)
                first = i;

            last = i;
        }
    }

    if (first < 0)
        return { 0, numSamples };

    const int window = std::max (0, maxSearchSamples);

    int start = first;
    if (const int crossing = detail::zeroCrossingBackward (mono, numSamples, first, window); crossing >= 0)
        start = crossing;

    int end = last + 1;
    if (end < numSamples)
        if (const int crossing = detail::zeroCrossingForward (mono, numSamples, end, window); crossing >= 0)
            end = crossing;

    return { start, end };
}

} // namespace snapplay::core
