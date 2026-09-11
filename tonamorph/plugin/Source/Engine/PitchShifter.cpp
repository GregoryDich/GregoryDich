#include "Engine/PitchShifter.h"

#if TONAMORPH_HAS_RUBBERBAND
 #include <rubberband/RubberBandStretcher.h>
#endif

#include <cmath>
#include <vector>

// The R3 ("finer") engine and its option flag arrived with Rubber Band 3.0 (API 2.7).
#if TONAMORPH_HAS_RUBBERBAND && defined (RUBBERBAND_API_MAJOR_VERSION) && defined (RUBBERBAND_API_MINOR_VERSION) \
    && (RUBBERBAND_API_MAJOR_VERSION > 2 || (RUBBERBAND_API_MAJOR_VERSION == 2 && RUBBERBAND_API_MINOR_VERSION >= 7))
 #define TONAMORPH_RUBBERBAND_HAS_R3 1
#else
 #define TONAMORPH_RUBBERBAND_HAS_R3 0
#endif

namespace tonamorph::engine
{

namespace
{
    /** Frames handed to the backend per call; bounds the temporaries to a few KB per channel. */
    constexpr int blockSize = 4096;

    juce::AudioBuffer<float> copyOf (const juce::AudioBuffer<float>& input)
    {
        juce::AudioBuffer<float> output;
        output.makeCopyOf (input);
        return output;
    }

#if TONAMORPH_HAS_RUBBERBAND
    /** Offline two-pass Rubber Band shift. Offline mode pads and delay-compensates
        internally (getStartDelay() is 0 there), and setExpectedInputDuration() makes the
        output frame count match the input; any residual difference is trimmed or zero-padded
        so the result length always equals the input length. */
    juce::AudioBuffer<float> shiftWithRubberBand (const juce::AudioBuffer<float>& input, double sampleRate,
                                                  double pitchScale, const PitchShifter::Options& options)
    {
        using Stretcher = RubberBand::RubberBandStretcher;

        const int numChannels = input.getNumChannels();
        const int numSamples = input.getNumSamples();

        int stretcherOptions = Stretcher::OptionProcessOffline | Stretcher::OptionPitchHighQuality;
        stretcherOptions |= options.preserveFormants ? Stretcher::OptionFormantPreserved
                                                     : Stretcher::OptionFormantShifted;
        if (numChannels > 1)
            stretcherOptions |= Stretcher::OptionChannelsTogether;

       #if TONAMORPH_RUBBERBAND_HAS_R3
        if (options.highQuality)
            stretcherOptions |= Stretcher::OptionEngineFiner;
       #endif

        Stretcher stretcher (static_cast<size_t> (std::lround (sampleRate)),
                             static_cast<size_t> (numChannels),
                             static_cast<Stretcher::Options> (stretcherOptions));
        stretcher.setTimeRatio (1.0);
        stretcher.setPitchScale (pitchScale);
        stretcher.setExpectedInputDuration (static_cast<size_t> (numSamples));
        stretcher.setMaxProcessSize (static_cast<size_t> (blockSize));

        std::vector<const float*> inputPointers (static_cast<size_t> (numChannels), nullptr);
        std::vector<float*> outputPointers (static_cast<size_t> (numChannels), nullptr);

        const auto pointInputAt = [&] (int offset)
        {
            for (int channel = 0; channel < numChannels; ++channel)
                inputPointers[static_cast<size_t> (channel)] = input.getReadPointer (channel, offset);
        };

        for (int offset = 0; offset < numSamples; offset += blockSize)
        {
            const int count = juce::jmin (blockSize, numSamples - offset);
            pointInputAt (offset);
            stretcher.study (inputPointers.data(), static_cast<size_t> (count), offset + count >= numSamples);
        }

        juce::AudioBuffer<float> output (numChannels, numSamples);
        output.clear();
        juce::AudioBuffer<float> retrieved (numChannels, blockSize);
        int written = 0;

        const auto drain = [&]
        {
            for (;;)
            {
                const int available = stretcher.available();   // 0: needs input, -1: finished

                if (available <= 0)
                    return;

                for (int channel = 0; channel < numChannels; ++channel)
                    outputPointers[static_cast<size_t> (channel)] = retrieved.getWritePointer (channel);

                const auto got = static_cast<int> (stretcher.retrieve (outputPointers.data(),
                                                                       static_cast<size_t> (juce::jmin (available, blockSize))));
                if (got <= 0)
                    return;

                const int toCopy = juce::jmin (got, numSamples - written);

                for (int channel = 0; channel < numChannels && toCopy > 0; ++channel)
                    output.copyFrom (channel, written, retrieved, channel, 0, toCopy);

                written += juce::jmax (0, toCopy);
            }
        };

        for (int offset = 0; offset < numSamples; offset += blockSize)
        {
            const int count = juce::jmin (blockSize, numSamples - offset);
            pointInputAt (offset);
            stretcher.process (inputPointers.data(), static_cast<size_t> (count), offset + count >= numSamples);
            drain();
        }

        drain();
        return output;
    }
#else
    /** Resampling fallback: reading the input `pitchScale` times faster raises the pitch and
        shortens the result to round(length / pitchScale) samples. Lagrange interpolation,
        processed in blocks; no anti-alias filtering. */
    juce::AudioBuffer<float> shiftByResampling (const juce::AudioBuffer<float>& input, double pitchScale)
    {
        const int numChannels = input.getNumChannels();
        const int numSamples = input.getNumSamples();
        const int outputLength = juce::jmax (1, static_cast<int> (std::llround (static_cast<double> (numSamples) / pitchScale)));

        juce::AudioBuffer<float> output (numChannels, outputLength);
        output.clear();

        for (int channel = 0; channel < numChannels; ++channel)
        {
            juce::LagrangeInterpolator interpolator;
            interpolator.reset();

            int inputPosition = 0;
            int outputPosition = 0;

            while (outputPosition < outputLength)
            {
                const int count = juce::jmin (blockSize, outputLength - outputPosition);
                const int available = numSamples - inputPosition;

                if (available <= 0)
                    break;   // remaining output stays silent

                inputPosition += interpolator.process (pitchScale,
                                                       input.getReadPointer (channel, inputPosition),
                                                       output.getWritePointer (channel, outputPosition),
                                                       count, available, 0);
                outputPosition += count;
            }
        }

        return output;
    }
#endif
} // namespace

bool PitchShifter::hasRubberBand() noexcept
{
#if TONAMORPH_HAS_RUBBERBAND
    return true;
#else
    return false;
#endif
}

juce::AudioBuffer<float> PitchShifter::shift (const juce::AudioBuffer<float>& input, double sampleRate,
                                              double semitones, const Options& options)
{
    if (input.getNumChannels() <= 0 || input.getNumSamples() <= 0
        || sampleRate <= 0.0 || ! std::isfinite (semitones) || std::abs (semitones) < 1.0e-6)
        return copyOf (input);

    const double pitchScale = std::pow (2.0, semitones / 12.0);

#if TONAMORPH_HAS_RUBBERBAND
    return shiftWithRubberBand (input, sampleRate, pitchScale, options);
#else
    juce::ignoreUnused (options);
    return shiftByResampling (input, pitchScale);
#endif
}

juce::AudioBuffer<float> PitchShifter::shift (const juce::AudioBuffer<float>& input, double sampleRate, double semitones)
{
    return shift (input, sampleRate, semitones, Options{});
}

juce::String PitchShifter::getBackendName()
{
    return hasRubberBand() ? "rubberband" : "resample";
}

} // namespace tonamorph::engine
