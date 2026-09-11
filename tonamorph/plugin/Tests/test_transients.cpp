#include "TestFramework.h"

#include "Core/TransientDetector.h"

#include <cmath>
#include <vector>

namespace
{

constexpr double sampleRate = 44100.0;
constexpr double twoPi = 6.283185307179586;

/** Adds a 3 ms decaying 2 kHz burst starting at `seconds`. */
void addClick (std::vector<float>& buffer, double seconds, double amplitude = 0.8)
{
    const auto start = static_cast<std::size_t> (seconds * sampleRate);
    const auto length = static_cast<std::size_t> (0.003 * sampleRate);

    for (std::size_t i = 0; i < length && start + i < buffer.size(); ++i)
    {
        const double t = static_cast<double> (i) / sampleRate;
        buffer[start + i] += static_cast<float> (amplitude * std::exp (-t / 0.001) * std::sin (twoPi * 2000.0 * t));
    }
}

void addTone (std::vector<float>& buffer, double from, double to, double frequency, double amplitude)
{
    const auto start = static_cast<std::size_t> (from * sampleRate);
    const auto end = std::min (buffer.size(), static_cast<std::size_t> (to * sampleRate));

    for (std::size_t i = start; i < end; ++i)
        buffer[i] += static_cast<float> (amplitude * std::sin (twoPi * frequency * static_cast<double> (i - start) / sampleRate));
}

bool containsOnsetNear (const std::vector<double>& onsets, double seconds, double tolerance = 0.010)
{
    for (const double onset : onsets)
        if (std::fabs (onset - seconds) <= tolerance)
            return true;

    return false;
}

} // namespace

TONAMORPH_TEST(radix2FftLocatesASinusoid)
{
    std::vector<double> re (1024), im (1024, 0.0);
    for (std::size_t i = 0; i < re.size(); ++i)
        re[i] = std::cos (twoPi * 10.0 * static_cast<double> (i) / 1024.0);

    tonamorph::core::detail::fftInPlace (re, im);

    const auto magnitude = [&] (std::size_t k) { return std::sqrt (re[k] * re[k] + im[k] * im[k]); };
    TONAMORPH_CHECK_NEAR (magnitude (10), 512.0, 1e-6);
    TONAMORPH_CHECK_NEAR (magnitude (1014), 512.0, 1e-6);
    TONAMORPH_CHECK_NEAR (magnitude (9), 0.0, 1e-6);
    TONAMORPH_CHECK_NEAR (magnitude (20), 0.0, 1e-6);
    TONAMORPH_CHECK_NEAR (magnitude (0), 0.0, 1e-6);
}

TONAMORPH_TEST(transientsOnSyntheticClicksAreFoundWithinTenMilliseconds)
{
    std::vector<float> buffer (static_cast<std::size_t> (1.2 * sampleRate), 0.0f);
    const std::vector<double> expected { 0.100, 0.350, 0.800 };
    for (const double t : expected)
        addClick (buffer, t);

    const auto onsets = tonamorph::core::detectTransients (buffer.data(), static_cast<int> (buffer.size()), sampleRate);

    TONAMORPH_CHECK_EQ (onsets.size(), expected.size());
    for (std::size_t i = 0; i < expected.size() && i < onsets.size(); ++i)
        TONAMORPH_CHECK_NEAR (onsets[i], expected[i], 0.010);

    for (std::size_t i = 1; i < onsets.size(); ++i)
        TONAMORPH_CHECK (onsets[i] > onsets[i - 1]);
}

TONAMORPH_TEST(transientsCloserThanThirtyMillisecondsMerge)
{
    std::vector<float> buffer (static_cast<std::size_t> (1.0 * sampleRate), 0.0f);
    addClick (buffer, 0.500);
    addClick (buffer, 0.520);

    const auto onsets = tonamorph::core::detectTransients (buffer.data(), static_cast<int> (buffer.size()), sampleRate);
    TONAMORPH_CHECK_EQ (onsets.size(), 1u);
    TONAMORPH_CHECK (containsOnsetNear (onsets, 0.500));
}

TONAMORPH_TEST(transientsOfToneOnsetAndOverBackground)
{
    std::vector<float> tone (static_cast<std::size_t> (1.2 * sampleRate), 0.0f);
    addTone (tone, 0.5, 1.0, 440.0, 0.5);

    const auto toneOnsets = tonamorph::core::detectTransients (tone.data(), static_cast<int> (tone.size()), sampleRate);
    TONAMORPH_CHECK_EQ (toneOnsets.size(), 1u);
    TONAMORPH_CHECK (containsOnsetNear (toneOnsets, 0.5));

    // A tone that stops is not an onset: the offset smears energy across bins (positive flux)
    // but the frame loses energy, so only the tone's start is reported.
    TONAMORPH_CHECK (! containsOnsetNear (toneOnsets, 1.0));

    // Clicks on top of a sustained tone that starts at t = 0 (itself an onset).
    std::vector<float> mixed (static_cast<std::size_t> (1.2 * sampleRate), 0.0f);
    addTone (mixed, 0.0, 1.2, 220.0, 0.3);
    addClick (mixed, 0.400);
    addClick (mixed, 0.900);

    const auto mixedOnsets = tonamorph::core::detectTransients (mixed.data(), static_cast<int> (mixed.size()), sampleRate);
    TONAMORPH_CHECK_EQ (mixedOnsets.size(), 3u);
    TONAMORPH_CHECK (containsOnsetNear (mixedOnsets, 0.0));
    TONAMORPH_CHECK (containsOnsetNear (mixedOnsets, 0.400));
    TONAMORPH_CHECK (containsOnsetNear (mixedOnsets, 0.900));
}

TONAMORPH_TEST(transientsDegenerateInputs)
{
    const std::vector<float> silence (44100, 0.0f);
    TONAMORPH_CHECK (tonamorph::core::detectTransients (silence.data(), 44100, sampleRate).empty());
    TONAMORPH_CHECK (tonamorph::core::detectTransients (nullptr, 0, sampleRate).empty());
    TONAMORPH_CHECK (tonamorph::core::detectTransients (silence.data(), 44100, 0.0).empty());

    const std::vector<float> quiet (44100, 0.0002f);   // DC far below -60 dBFS
    TONAMORPH_CHECK (tonamorph::core::detectTransients (quiet.data(), 44100, sampleRate).empty());
}

TONAMORPH_TEST(slicesFromTransientsBuildContiguousRanges)
{
    using tonamorph::core::slicesFromTransients;

    const auto slices = slicesFromTransients ({ 0.1, 0.5, 0.9 }, 1.2);
    TONAMORPH_CHECK_EQ (slices.size(), 3u);
    TONAMORPH_CHECK_NEAR (slices[0].startSeconds, 0.1, 1e-12);
    TONAMORPH_CHECK_NEAR (slices[0].endSeconds, 0.5, 1e-12);
    TONAMORPH_CHECK_EQ (slices[0].midiNote, 36);
    TONAMORPH_CHECK_NEAR (slices[1].startSeconds, 0.5, 1e-12);
    TONAMORPH_CHECK_NEAR (slices[1].endSeconds, 0.9, 1e-12);
    TONAMORPH_CHECK_EQ (slices[1].midiNote, 37);
    TONAMORPH_CHECK_NEAR (slices[2].startSeconds, 0.9, 1e-12);
    TONAMORPH_CHECK_NEAR (slices[2].endSeconds, 1.2, 1e-12);
    TONAMORPH_CHECK_EQ (slices[2].midiNote, 38);

    TONAMORPH_CHECK (slicesFromTransients ({}, 1.0).empty());

    const auto filtered = slicesFromTransients ({ 1.5, -0.1, 0.2, 0.2 }, 1.0, 60);   // unsorted, duplicate, out of range
    TONAMORPH_CHECK_EQ (filtered.size(), 1u);
    TONAMORPH_CHECK_NEAR (filtered[0].startSeconds, 0.2, 1e-12);
    TONAMORPH_CHECK_NEAR (filtered[0].endSeconds, 1.0, 1e-12);
    TONAMORPH_CHECK_EQ (filtered[0].midiNote, 60);

    const auto capped = slicesFromTransients ({ 0.0, 0.1, 0.2, 0.3, 0.4 }, 1.0, 126);   // only 2 notes left
    TONAMORPH_CHECK_EQ (capped.size(), 2u);
    TONAMORPH_CHECK_EQ (capped[1].midiNote, 127);
    TONAMORPH_CHECK_NEAR (capped[1].endSeconds, 1.0, 1e-12);
}
