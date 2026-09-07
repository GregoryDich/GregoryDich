#pragma once

/**
 * Offline pitch shifting used when building StemSound key zones (contract §8 root
 * transposition: `semitones = target_root_midi - stem.root_midi`).
 *
 * Uses the Rubber Band Library (R3 engine, offline mode, duration preserved) when the
 * build defines SNAPPLAY_HAS_RUBBERBAND=1, otherwise falls back to Lagrange resampling,
 * which changes the duration by 2^(-semitones/12). Never call from the audio thread.
 */

#include <JuceHeader.h>

namespace snapplay::engine
{

class PitchShifter
{
public:
    struct Options
    {
        bool preserveFormants = false;   ///< Rubber Band only
        bool highQuality = true;         ///< Rubber Band: R3 engine with finer pitch options
    };

    /** True when the Rubber Band backend is compiled in. */
    static bool hasRubberBand() noexcept;

    /** Returns `input` transposed by `semitones` (may be fractional, negative allowed).
        A shift of 0 returns a copy. Channel count is preserved; the output length equals
        the input length with Rubber Band and `round(length / 2^(semitones/12))` with the
        resampling fallback. */
    static juce::AudioBuffer<float> shift (const juce::AudioBuffer<float>& input, double sampleRate,
                                           double semitones, const Options& options);
    /** Same with default Options. */
    static juce::AudioBuffer<float> shift (const juce::AudioBuffer<float>& input, double sampleRate,
                                           double semitones);

    /** Name of the active backend for diagnostics: "rubberband" or "resample". */
    static juce::String getBackendName();

private:
    PitchShifter() = delete;
};

} // namespace snapplay::engine
