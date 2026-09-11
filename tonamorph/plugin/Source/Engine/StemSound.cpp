#include "Engine/StemSound.h"

#include "Core/Envelope.h"
#include "Core/ZeroCrossing.h"
#include "Engine/AutoAdsr.h"
#include "Engine/PitchShifter.h"

#include <cmath>

namespace tonamorph::engine
{

namespace
{
    /** Zones whose root lies within this many semitones of the target root get their own
        offline pitch shift (duration and formants preserved). Every such zone costs a full
        Rubber Band pass over the stem - with a cost that grows with the shift - plus a copy of
        it, so the keyboard beyond the window is covered by one wide zone per side rooted at
        the window's edge and played by realtime varispeed, like a classic sampler. */
    constexpr int offlineWindowSemitones = 12;
    constexpr float normalisePeakDb = -1.0f;

    struct ZoneSpec
    {
        int lowNote = 0;
        int highNote = 0;
        int rootMidi = 0;
    };

    int floorDiv (int value, int divisor) noexcept
    {
        return value >= 0 ? value / divisor : -((-value + divisor - 1) / divisor);
    }

    juce::AudioBuffer<float> mixToMono (const juce::AudioBuffer<float>& audio, int numChannels)
    {
        juce::AudioBuffer<float> mono (1, audio.getNumSamples());
        mono.clear();

        for (int channel = 0; channel < numChannels; ++channel)
            mono.addFrom (0, 0, audio, channel, 0, audio.getNumSamples(), 1.0f / static_cast<float> (numChannels));

        return mono;
    }

    /** Lays out zones of `zoneWidth` semitones on a grid aligned so that one zone is rooted
        exactly at `targetRoot`, clips them to [lowestNote, highestNote] and merges the zones
        outside the offline window into one zone per side. */
    std::vector<ZoneSpec> layoutZones (int lowestNote, int highestNote, int zoneWidth, int targetRoot)
    {
        const int halfWidth = zoneWidth / 2;
        const int gridOrigin = targetRoot - halfWidth;

        std::vector<ZoneSpec> below, inside, above;

        for (int low = gridOrigin + floorDiv (lowestNote - gridOrigin, zoneWidth) * zoneWidth;
             low <= highestNote; low += zoneWidth)
        {
            ZoneSpec zone;
            zone.lowNote = juce::jmax (low, lowestNote);
            zone.highNote = juce::jmin (low + zoneWidth - 1, highestNote);
            zone.rootMidi = juce::jlimit (0, 127, low + halfWidth);

            const int distance = zone.rootMidi - targetRoot;

            if (distance < -offlineWindowSemitones)
                below.push_back (zone);
            else if (distance > offlineWindowSemitones)
                above.push_back (zone);
            else
                inside.push_back (zone);
        }

        std::vector<ZoneSpec> zones;
        zones.reserve (inside.size() + 2);

        if (! below.empty())
            zones.push_back ({ below.front().lowNote, below.back().highNote, below.back().rootMidi });

        zones.insert (zones.end(), inside.begin(), inside.end());

        if (! above.empty())
            zones.push_back ({ above.front().lowNote, above.back().highNote, above.front().rootMidi });

        return zones;
    }
} // namespace

std::shared_ptr<const StemSound> StemSound::build (const juce::AudioBuffer<float>& source, double sampleRateToUse,
                                                   const cloud::StemInfo& info, const BuildOptions& options)
{
    const int sourceChannels = source.getNumChannels();
    const int sourceLength = source.getNumSamples();

    if (sourceChannels <= 0 || sourceLength <= 0 || sampleRateToUse <= 0.0)
        return nullptr;

    const int numChannels = juce::jlimit (1, juce::jmax (1, options.maxChannels), sourceChannels);
    const int lowestNote = juce::jlimit (0, 127, juce::jmin (options.lowestNote, options.highestNote));
    const int highestNote = juce::jlimit (0, 127, juce::jmax (options.lowestNote, options.highestNote));
    const int zoneWidth = juce::jmax (1, options.zoneWidthSemitones);
    const int targetRoot = juce::jlimit (0, 127, options.targetRootMidi);

    // 1. Audible region, snapped to zero crossings.
    core::TrimRange range { 0, sourceLength };

    if (options.trimToZeroCrossings)
    {
        const auto mono = mixToMono (source, numChannels);
        range = core::findTrimRange (mono.getReadPointer (0), sourceLength, options.trimThreshold);
        range.start = juce::jlimit (0, sourceLength, range.start);
        range.end = juce::jlimit (range.start, sourceLength, range.end);

        if (range.length() <= 0)
            range = { 0, sourceLength };
    }

    // 2. Trimmed copy, normalised to -1 dBFS peak.
    juce::AudioBuffer<float> trimmed (numChannels, range.length());

    for (int channel = 0; channel < numChannels; ++channel)
        trimmed.copyFrom (channel, 0, source, channel, range.start, range.length());

    const float peak = trimmed.getMagnitude (0, trimmed.getNumSamples());

    if (peak > 1.0e-6f)
        trimmed.applyGain (juce::Decibels::decibelsToGain (normalisePeakDb) / peak);

    // 3. Envelope: the server's suggestion or one derived from the audio.
    const core::Adsr adsr = resolveAdsr (info, trimmed, sampleRateToUse);

    PitchShifter::Options shiftOptions;
    shiftOptions.preserveFormants = info.name == "vocals";

    const auto shifted = [&] (int semitones) -> juce::AudioBuffer<float>
    {
        if (semitones == 0)
        {
            juce::AudioBuffer<float> copy;
            copy.makeCopyOf (trimmed);
            return copy;
        }

        return PitchShifter::shift (trimmed, sampleRateToUse, semitones, shiftOptions);
    };

    // 4. Base sample: the stem's detected root moved to the target root.
    std::shared_ptr<StemSound> sound (new StemSound());
    sound->name = info.name;
    sound->sampleRate = sampleRateToUse;
    sound->numChannels = numChannels;
    sound->rootMidi = targetRoot;
    sound->sourceRootMidi = info.rootMidi;
    sound->adsr = adsr;
    sound->sample = shifted (targetRoot - info.rootMidi);

    // 5. Key zones, each shifted from the original audio in a single pass.
    const auto layout = layoutZones (lowestNote, highestNote, zoneWidth, targetRoot);
    sound->zones.reserve (layout.size());

    for (const auto& spec : layout)
    {
        KeyZone zone;
        zone.lowNote = spec.lowNote;
        zone.highNote = spec.highNote;
        zone.zoneRootMidi = spec.rootMidi;

        if (spec.rootMidi == targetRoot)
            zone.audio.makeCopyOf (sound->sample);
        else
            zone.audio = shifted (spec.rootMidi - info.rootMidi);

        sound->zones.push_back (std::move (zone));
    }

    return sound;
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

} // namespace tonamorph::engine
