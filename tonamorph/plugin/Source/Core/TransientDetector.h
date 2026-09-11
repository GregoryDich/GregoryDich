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

namespace tonamorph::core
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

/** One analysis frame: its half-wave rectified flux and the energy of its spectrum. */
struct FluxFrame
{
    double flux = 0.0;
    double energy = 0.0;
};

/**
 * Half-wave rectified spectral flux per analysis frame (Hann window, frames start at
 * multiples of the hop, zero-padded past the end of the signal). The first frame is
 * compared against silence so a signal that starts abruptly at t = 0 registers an onset.
 * The frame energy travels with each frame so callers can reject note offsets, whose
 * truncated partials smear across bins — raising the flux — while the energy falls.
 */
inline std::vector<FluxFrame> spectralFlux (const float* mono, int numSamples)
{
    constexpr int frameSize = transientFrameSize;
    constexpr int hop = transientHopSize;
    constexpr std::size_t numBins = static_cast<std::size_t> (frameSize / 2 + 1);

    std::vector<double> window (static_cast<std::size_t> (frameSize));
    for (int i = 0; i < frameSize; ++i)
        window[static_cast<std::size_t> (i)] = 0.5 * (1.0 - std::cos (2.0 * transientPi * static_cast<double> (i)
                                                                      / static_cast<double> (frameSize)));

    const int numFrames = (numSamples + hop - 1) / hop;
    std::vector<FluxFrame> frames;
    frames.reserve (static_cast<std::size_t> (numFrames));

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

        FluxFrame result;
        for (std::size_t k = 0; k < numBins; ++k)
        {
            current[k] = std::sqrt (re[k] * re[k] + im[k] * im[k]);
            result.flux += std::max (0.0, current[k] - previous[k]);
            result.energy += current[k] * current[k];
        }

        frames.push_back (result);
        std::swap (previous, current);
    }

    return frames;
}

/**
 * Locates the onset inside the frame starting at `frameStart`: the first 32-sample block whose
 * mean energy crosses the midpoint between the quietest and the loudest block of that frame.
 * A frame is only flagged when its energy rose, so its loudest block belongs to the new event
 * and its quietest one to whatever was sounding before — the midpoint separates the two even
 * when the new event arrives over a sustained background.
 */
inline double refineOnset (const float* mono, int numSamples, int frameStart, double sampleRate)
{
    constexpr int blockSize = 32;

    const int frameEnd = std::min (numSamples, frameStart + transientFrameSize);
    const int numBlocks = std::max (1, (frameEnd - frameStart) / blockSize);

    std::vector<double> energies (static_cast<std::size_t> (numBlocks), 0.0);
    for (int block = 0; block < numBlocks; ++block)
    {
        const int start = frameStart + block * blockSize;
        double sum = 0.0;

        for (int i = 0; i < blockSize && start + i < frameEnd; ++i)
        {
            const double sample = mono[start + i];
            sum += sample * sample;
        }

        energies[static_cast<std::size_t> (block)] = sum / blockSize;
    }

    const auto [quietest, loudest] = std::minmax_element (energies.begin(), energies.end());
    const double threshold = 0.5 * (*quietest + *loudest);

    for (int block = 0; block < numBlocks; ++block)
        if (energies[static_cast<std::size_t> (block)] >= threshold)
            return static_cast<double> (frameStart + block * blockSize) / sampleRate;

    return static_cast<double> (frameStart) / sampleRate;
}

} // namespace detail

/**
 * Detects transient onsets in a mono signal.
 *
 * Spectral-flux method: 1024-sample Hann-windowed frames every 256 samples (radix-2 FFT),
 * half-wave rectified flux of the magnitude spectra, and an adaptive threshold of
 * `0.02 * max flux + 1.5 * median (flux over +-8 frames)` plus a -60 dBFS floor. A frame is
 * an onset when its flux is a local maximum above that threshold and its spectrum is louder
 * carries more energy than the previous frame's — the energy test rejects note offsets, whose
 * truncated partials smear across bins and so produce positive flux as well. The onset time is
 * refined from the detected frame's start to the first 32-sample block inside it whose energy
 * crosses the midpoint between that frame's quietest and loudest block, which locates onsets to
 * a few milliseconds. Onsets closer than 30 ms to the previous one are dropped.
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

    const std::vector<detail::FluxFrame> frames = detail::spectralFlux (mono, numSamples);
    const int numFrames = static_cast<int> (frames.size());

    std::vector<double> flux (frames.size());
    for (std::size_t i = 0; i < frames.size(); ++i)
        flux[i] = frames[i].flux;

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

        // A note offset smears its truncated partials across bins, which also raises the flux;
        // only a frame carrying more energy than its predecessor is a real onset.
        const double previousEnergy = frame > 0 ? frames[static_cast<std::size_t> (frame - 1)].energy : 0.0;
        if (frames[static_cast<std::size_t> (frame)].energy <= previousEnergy)
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

} // namespace tonamorph::core
