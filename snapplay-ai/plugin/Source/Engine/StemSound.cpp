#include "Engine/StemSound.h"

#include "Core/Envelope.h"
#include "Core/ZeroCrossing.h"
#include "Engine/PitchShifter.h"

#include <cmath>

namespace snapplay::engine
{

std::shared_ptr<const StemSound> StemSound::build (const juce::AudioBuffer<float>& source, double sampleRateToUse,
                                                   const cloud::StemInfo& info, const BuildOptions& options)
{
    juce::ignoreUnused (source, sampleRateToUse, info, options);
    return nullptr;
}

std::shared_ptr<const StemSound> StemSound::fromPreparedSample (juce::AudioBuffer<float> preparedSample, double sampleRateToUse,
                                                                int rootMidiToUse, const core::Adsr& adsrToUse,
                                                                const juce::String& nameToUse)
{
    std::shared_ptr<StemSound> sound (new StemSound());
    sound->name = nameToUse;
    sound->sampleRate = sampleRateToUse;
    sound->numChannels = preparedSample.getNumChannels();
    sound->rootMidi = rootMidiToUse;
    sound->sourceRootMidi = rootMidiToUse;
    sound->adsr = adsrToUse;
    sound->sample = std::move (preparedSample);

    KeyZone zone;
    zone.lowNote = 0;
    zone.highNote = 127;
    zone.zoneRootMidi = rootMidiToUse;
    zone.audio.makeCopyOf (sound->sample);
    sound->zones.push_back (std::move (zone));

    return sound;
}

double StemSound::getLengthInSeconds() const noexcept
{
    return sampleRate > 0.0 ? static_cast<double> (sample.getNumSamples()) / sampleRate : 0.0;
}

const StemSound::KeyZone* StemSound::zoneForNote (int midiNote) const noexcept
{
    for (const auto& zone : zones)
        if (midiNote >= zone.lowNote && midiNote <= zone.highNote)
            return &zone;

    return nullptr;
}

double StemSound::playbackRatioFor (int midiNote, const KeyZone& zone) noexcept
{
    return std::pow (2.0, static_cast<double> (midiNote - zone.zoneRootMidi) / 12.0);
}

} // namespace snapplay::engine
