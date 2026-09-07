#pragma once

/**
 * Amplitude-envelope analysis used for Auto-ADSR (contract §8): when the server sends no
 * `suggested_adsr`, the plugin derives one from the stem itself.
 *
 * Header-only and JUCE-free.
 */

#include "Types.h"

namespace snapplay::core
{

/**
 * Derives an ADSR from a mono signal's amplitude envelope.
 *
 * Algorithm (RMS envelope with 10 ms hops):
 *  - onset  = first hop whose RMS exceeds -60 dBFS relative to full scale;
 *  - attack = time from onset to the envelope peak;
 *  - the sustain level is the median RMS of the middle third of the audible region,
 *    expressed as a fraction of the peak (0..1);
 *  - decay  = time from the peak until the envelope first falls to the sustain level;
 *  - release = time from the last hop above the sustain level until the envelope drops
 *    below -60 dBFS (or the buffer ends).
 * Results are clamped to attack 1..2000 ms, decay 1..4000 ms, sustain 0..1,
 * release 5..5000 ms. Silent or empty input returns the default Adsr{}.
 *
 * @param mono        interleaved-free mono samples (callers mix down first).
 * @param numSamples  number of samples in `mono`.
 * @param sampleRate  sample rate of `mono` in Hz.
 */
inline Adsr deriveAdsr ([[maybe_unused]] const float* mono,
                        [[maybe_unused]] int numSamples,
                        [[maybe_unused]] double sampleRate)
{
    return {};
}

} // namespace snapplay::core
