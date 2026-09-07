#pragma once

/**
 * Client-side transient detection and slicing for drum mode (contract §8: when the server
 * reports no `slices`, slice locally from `transients_seconds`, or detect transients here).
 *
 * Header-only and JUCE-free.
 */

#include "Types.h"

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <vector>

namespace snapplay::core
{

namespace detail
{

inline constexpr int transientFrameSize = 1024;
inline constexpr int transientHopSize = 256;
inline constexpr double transientPi = 3.14159265358979323846;

/** In-place iterative radix-2 FFT; `re` / `im` must have the same power-of-two size. */
inline void fftInPlace (std::vector<double>& re, std::vector<double>& im)
{
    const std::size_t n = re.size();

    for (std::size_t i = 1, j = 0; i < n; ++i)
    {
        std::size_t bit = n >> 1;
        for (; (j & bit) != 0; bit >>= 1)
            j ^= bit;
        j ^= bit;

        if (i < j)
        {
            std::swap (re[i], re[j]);
            std::swap (im[i], im[j]);
        }
    }

    std::vector<double> twiddleRe (n / 2), twiddleIm (n / 2);
    for (std::size_t k = 0; k < n / 2; ++k)
    {
        const double angle = -2.0 * transientPi * static_cast<double> (k) / static_cast<double> (n);
        twiddleRe[k] = std::cos (angle);
        twiddleIm[k] = std::sin (angle);
    }

    for (std::size_t len = 2; len <= n; len <<= 1)
    {
        const std::size_t half = len / 2;
        const std::size_t stride = n / len;

        for (std::size_t block = 0; block < n; block += len)
        {
            for (std::size_t j = 0; j < half; ++j)
            {
                const std::size_t a = block + j;
                const std::size_t b = a + half;
                const double wr = twiddleRe[j * stride];
                const double wi = twiddleIm[j * stride];
                const double tr = re[b] * wr - im[b] * wi;
                const double ti = re[b] * wi + im[b] * wr;
                re[b] = re[a] - tr;
                im[b] = im[a] - ti;
                re[a] += tr;
                im[a] += ti;
            }
        }
    }
}

/**
 * Half-wave rectified spectral flux per analysis frame (Hann window, frames start at
 * multiples of the hop, zero-padded past the end of the signal). The first frame is
 * compared against silence so a signal that starts abruptly at t = 0 registers an onset.
 */
inline std::vector<double> spectralFlux (const float* mono, int numSamples)
{
    constexpr int frameSize = transientFrameSize;
    constexpr int hop = transientHopSize;
    constexpr std::size_t numBins = static_cast<std::size_t> (frameSize / 2 + 1);

    std::vector<double> window (static_cast<std::size_t> (frameSize));
    for (int i = 0; i < frameSize; ++i)
        window[static_cast<std::size_t> (i)] = 0.5 * (1.0 - std::cos (2.0 * transientPi * static_cast<double> (i)
                                                                      / static_cast<double> (frameSize)));

    const int numFrames = (numSamples + hop - 1) / hop;
    std::vector<double> flux;
    flux.reserve (static_cast<std::size_t> (numFrames));

    std::vector<double> re (static_cast<std::size_t> (frameSize)), im (static_cast<std::size_t> (frameSize));
    std::vector<double> previous (numBins, 0.0), current (numBins, 0.0);

    for (int frame = 0; frame < numFrames; ++frame)
    {
        const int start = frame * hop;
        const int available = std::min (frameSize, numSamples - start);

        for (int i = 0; i < frameSize; ++i)
        {
            re[static_cast<std::size_t> (i)] = i < available ? static_cast<double> (mono[start + i]) * window[static_cast<std::size_t> (i)]
                                                             : 0.0;
            im[static_cast<std::size_t> (i)] = 0.0;
        }

        fftInPlace (re, im);

        double sum = 0.0;
        for (std::size_t k = 0; k < numBins; ++k)
        {
            current[k] = std::sqrt (re[k] * re[k] + im[k] * im[k]);
            sum += std::max (0.0, current[k] - previous[k]);
        }

        flux.push_back (sum);
        std::swap (previous, current);
    }

    return flux;
}

/**
 * Refines an onset inside the frame starting at `frameStart` to the start of the 32-sample
 * block with the largest rise in mean energy over its predecessor (the block before the
 * frame, or silence at the very beginning).
 */
inline double refineOnset (const float* mono, int numSamples, int frameStart, double sampleRate)
{
    constexpr int block = 32;

    const auto meanEnergy = [mono] (int start, int count)
    {
        double sum = 0.0;
        for (int i = 0; i < count; ++i)
        {
            const double sample = mono[start + i];
            sum += sample * sample;
        }
        return count > 0 ? sum / static_cast<double> (count) : 0.0;
    };

    const int frameEnd = std::min (numSamples, frameStart + transientFrameSize);
    double previous = frameStart >= block ? meanEnergy (frameStart - block, block) : 0.0;
    double bestRise = -1.0;
    int bestStart = frameStart;

    for (int start = frameStart; start < frameEnd; start += block)
    {
        const double energy = meanEnergy (start, std::min (block, frameEnd - start));
        const double rise = energy - previous;

        if (rise > bestRise)
        {
            bestRise = rise;
            bestStart = start;
        }

        previous = energy;
    }

    return static_cast<double> (bestStart) / sampleRate;
}

} // namespace detail

/**
 * Detects transient onsets in a mono signal.
 *
 * Spectral-flux method: 1024-sample Hann-windowed frames every 256 samples (radix-2 FFT),
 * half-wave rectified flux of the magnitude spectra, and an adaptive threshold of
 * `0.02 * max flux + 1.5 * median (flux over +-8 frames)` plus a -60 dBFS floor. A frame
 * whose flux is a local maximum above the threshold is an onset; its time is refined to the
 * start of the 32-sample block inside that frame where the signal energy rises most, so
 * clicks are located to about a millisecond. Onsets closer than 30 ms to the previous one
 * are dropped.
 *
 * @return onset times in seconds, strictly increasing; empty for silent input.
 */
inline std::vector<double> detectTransients (const float* mono, int numSamples, double sampleRate)
{
    constexpr double minGapSeconds = 0.03;
    constexpr int medianRadius = 8;
    constexpr double medianWeight = 1.5;
    constexpr double relativeFloor = 0.02;
    constexpr double absoluteFloor = 1e-3 * static_cast<double> (detail::transientFrameSize / 2);   // -60 dBFS per bin

    if (mono == nullptr || numSamples <= 0 || ! (sampleRate > 0.0))
        return {};

    const std::vector<double> flux = detail::spectralFlux (mono, numSamples);
    const int numFrames = static_cast<int> (flux.size());
    const double maxFlux = *std::max_element (flux.begin(), flux.end());

    if (! (maxFlux >= absoluteFloor))
        return {};

    const double delta = relativeFloor * maxFlux;
    std::vector<double> neighbourhood;
    neighbourhood.reserve (static_cast<std::size_t> (2 * medianRadius + 1));
    std::vector<double> onsets;

    for (int frame = 0; frame < numFrames; ++frame)
    {
        const double value = flux[static_cast<std::size_t> (frame)];

        if (value < absoluteFloor)
            continue;

        if (frame > 0 && value < flux[static_cast<std::size_t> (frame - 1)])
            continue;

        if (frame + 1 < numFrames && value < flux[static_cast<std::size_t> (frame + 1)])
            continue;

        neighbourhood.assign (flux.begin() + std::max (0, frame - medianRadius),
                              flux.begin() + std::min (numFrames, frame + medianRadius + 1));
        const auto middle = neighbourhood.begin() + static_cast<std::ptrdiff_t> (neighbourhood.size() / 2);
        std::nth_element (neighbourhood.begin(), middle, neighbourhood.end());

        if (value <= delta + medianWeight * *middle)
            continue;

        const double onset = detail::refineOnset (mono, numSamples, frame * detail::transientHopSize, sampleRate);

        if (! onsets.empty() && onset - onsets.back() < minGapSeconds)
            continue;

        onsets.push_back (onset);
    }

    return onsets;
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
inline std::vector<Slice> slicesFromTransients (const std::vector<double>& transientsSeconds,
                                                double durationSeconds,
                                                int firstMidiNote = 36)
{
    const int firstNote = std::clamp (firstMidiNote, 0, 127);
    const auto maxSlices = static_cast<std::size_t> (128 - firstNote);

    std::vector<double> onsets;
    onsets.reserve (transientsSeconds.size());

    for (const double onset : transientsSeconds)
        if (std::isfinite (onset) && onset >= 0.0 && onset < durationSeconds)
            onsets.push_back (onset);

    std::sort (onsets.begin(), onsets.end());
    onsets.erase (std::unique (onsets.begin(), onsets.end()), onsets.end());

    if (onsets.size() > maxSlices)
        onsets.resize (maxSlices);

    std::vector<Slice> slices;
    slices.reserve (onsets.size());

    for (std::size_t i = 0; i < onsets.size(); ++i)
    {
        Slice slice;
        slice.startSeconds = onsets[i];
        slice.endSeconds = i + 1 < onsets.size() ? onsets[i + 1] : durationSeconds;
        slice.midiNote = firstNote + static_cast<int> (i);
        slices.push_back (slice);
    }

    return slices;
}

} // namespace snapplay::core
