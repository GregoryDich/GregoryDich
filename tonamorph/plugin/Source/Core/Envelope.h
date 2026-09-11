#pragma once

/**
 * Amplitude-envelope analysis used for Auto-ADSR (contract §8): when the server sends no
 * `suggested_adsr`, the plugin derives one from the stem itself.
 *
 * Header-only and JUCE-free.
 */

#include "Types.h"

#include <algorithm>
#include <cmath>
#include <vector>

namespace tonamorph::core
{

/**
 * Derives an ADSR from a mono signal's amplitude envelope.
 *
 * Algorithm (RMS envelope with 10 ms hops, -60 dBFS = 0.001 as the silence level):
 *  - the audible region runs from the first hop above the silence level to the last;
 *  - attack  = time from the start of the audible region until the envelope first reaches
 *              90 % of its peak;
 *  - the sustain level is the median RMS of the middle third of the audible region,
 *    expressed as a fraction of the peak (0..1);
 *  - decay   = time from the peak hop until the envelope first falls to the sustain level;
 *  - release = time from the end of the last sustained region (the last hop within ~1 dB of
 *              the sustain level) until the envelope drops below the silence level, or the
 *              buffer ends.
 * Results are clamped to attack 1..2000 ms, decay 1..4000 ms, sustain 0..1,
 * release 5..5000 ms. Degenerate input — a null or empty buffer, a non-positive sample
 * rate, silence, or an audible region shorter than three hops — returns the default Adsr{}.
 *
 * @param mono        interleaved-free mono samples (callers mix down first).
 * @param numSamples  number of samples in `mono`.
 * @param sampleRate  sample rate of `mono` in Hz.
 */
inline Adsr deriveAdsr (const float* mono, int numSamples, double sampleRate)
{
    constexpr double hopSeconds = 0.01;
    constexpr double silenceLevel = 0.001;      // -60 dBFS
    constexpr double attackTarget = 0.9;        // fraction of the peak that ends the attack
    constexpr double sustainTolerance = 0.89;   // ~1 dB below the sustain level still counts as sustained
    constexpr int minAudibleHops = 3;

    if (mono == nullptr || numSamples <= 0 || ! (sampleRate > 0.0))
        return {};

    const int hopSamples = std::max (1, static_cast<int> (std::lround (sampleRate * hopSeconds)));
    const double hopMs = 1000.0 * static_cast<double> (hopSamples) / sampleRate;

    std::vector<double> rms;
    rms.reserve (static_cast<std::size_t> (numSamples / hopSamples + 1));

    for (int start = 0; start < numSamples; start += hopSamples)
    {
        const int count = std::min (hopSamples, numSamples - start);
        double sum = 0.0;

        for (int i = 0; i < count; ++i)
        {
            const double sample = mono[start + i];
            sum += sample * sample;
        }

        rms.push_back (std::sqrt (sum / static_cast<double> (count)));
    }

    const int numHops = static_cast<int> (rms.size());
    const auto peakIt = std::max_element (rms.begin(), rms.end());
    const double peak = *peakIt;

    if (! (peak >= silenceLevel))
        return {};

    const int peakIndex = static_cast<int> (peakIt - rms.begin());

    int onset = 0;
    while (rms[static_cast<std::size_t> (onset)] < silenceLevel)
        ++onset;

    int lastAudible = numHops - 1;
    while (rms[static_cast<std::size_t> (lastAudible)] < silenceLevel)
        --lastAudible;

    const int audibleHops = lastAudible - onset + 1;
    if (audibleHops < minAudibleHops)
        return {};

    int attackEnd = onset;
    while (rms[static_cast<std::size_t> (attackEnd)] < attackTarget * peak)
        ++attackEnd;

    const int thirdStart = onset + audibleHops / 3;
    const int thirdEnd = std::max (thirdStart + 1, onset + (2 * audibleHops) / 3);
    std::vector<double> middle (rms.begin() + thirdStart, rms.begin() + thirdEnd);
    std::sort (middle.begin(), middle.end());
    const std::size_t half = middle.size() / 2;
    const double sustainLevel = middle.size() % 2 == 1 ? middle[half]
                                                        : 0.5 * (middle[half - 1] + middle[half]);

    int decayEnd = peakIndex;
    while (decayEnd < lastAudible && rms[static_cast<std::size_t> (decayEnd)] > sustainLevel)
        ++decayEnd;

    int lastSustained = lastAudible;
    while (lastSustained > peakIndex && rms[static_cast<std::size_t> (lastSustained)] < sustainTolerance * sustainLevel)
        --lastSustained;

    int releaseEnd = lastSustained + 1;
    while (releaseEnd < numHops && rms[static_cast<std::size_t> (releaseEnd)] >= silenceLevel)
        ++releaseEnd;

    Adsr adsr;
    adsr.attackMs = std::clamp (static_cast<double> (attackEnd - onset) * hopMs, 1.0, 2000.0);
    adsr.decayMs = std::clamp (static_cast<double> (decayEnd - peakIndex) * hopMs, 1.0, 4000.0);
    adsr.sustain = std::clamp (sustainLevel / peak, 0.0, 1.0);
    adsr.releaseMs = std::clamp (static_cast<double> (releaseEnd - lastSustained - 1) * hopMs, 5.0, 5000.0);
    return adsr;
}

} // namespace tonamorph::core
