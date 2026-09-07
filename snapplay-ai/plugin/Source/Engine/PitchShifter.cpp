#include "Engine/PitchShifter.h"

#if SNAPPLAY_HAS_RUBBERBAND
 #include <rubberband/RubberBandStretcher.h>
#endif

namespace snapplay::engine
{

bool PitchShifter::hasRubberBand() noexcept
{
#if SNAPPLAY_HAS_RUBBERBAND
    return true;
#else
    return false;
#endif
}

juce::AudioBuffer<float> PitchShifter::shift (const juce::AudioBuffer<float>& input, double sampleRate,
                                              double semitones, const Options& options)
{
    juce::ignoreUnused (sampleRate, semitones, options);

    juce::AudioBuffer<float> output;
    output.makeCopyOf (input);
    return output;
}

juce::AudioBuffer<float> PitchShifter::shift (const juce::AudioBuffer<float>& input, double sampleRate, double semitones)
{
    return shift (input, sampleRate, semitones, Options{});
}

juce::String PitchShifter::getBackendName()
{
    return hasRubberBand() ? "rubberband" : "resample";
}

} // namespace snapplay::engine
