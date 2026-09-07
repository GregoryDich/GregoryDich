#pragma once

/**
 * An immutable, fully prepared melodic sample: the stem trimmed at zero crossings,
 * transposed so its detected root lands on the target root (contract §8) and pre-shifted
 * into key zones so realtime varispeed never exceeds half a zone width.
 *
 * Built off the audio thread with build(); afterwards every accessor is const, lock-free
 * and allocation-free, so voices may read it on the audio thread.
 */

#include <JuceHeader.h>

#include "Cloud/Models.h"
#include "Core/Types.h"

#include <memory>
#include <vector>

namespace snapplay::engine
{

class StemSound
{
public:
    /** A pre-shifted copy of the sample covering a contiguous note range. Playing
        `zoneRootMidi` at playback ratio 1.0 sounds in tune; other notes in the range use
        `playbackRatioFor()`. */
    struct KeyZone
    {
        int lowNote = 0;
        int highNote = 127;
        int zoneRootMidi = 60;
        juce::AudioBuffer<float> audio;   ///< same channel count and sample rate as the sound
    };

    struct BuildOptions
    {
        int targetRootMidi = 48;         ///< `rootTarget` parameter; the note that plays the transposed root
        int zoneWidthSemitones = 4;      ///< key-zone span; varispeed stays within ±zoneWidth/2
        int lowestNote = 24;             ///< keyboard range covered by zones
        int highestNote = 108;
        bool trimToZeroCrossings = true;
        float trimThreshold = 0.001f;    ///< linear, -60 dBFS
        int maxChannels = 2;
    };

    /** Builds a sound from decoded stem audio. Transposes by
        `targetRootMidi - info.rootMidi` (PitchShifter), trims silence, derives the ADSR
        (`info.suggestedAdsr` or core::deriveAdsr) and creates the key zones. Returns
        nullptr for empty input. May take seconds; never call on the audio thread. */
    static std::shared_ptr<const StemSound> build (const juce::AudioBuffer<float>& source, double sampleRate,
                                                   const cloud::StemInfo& info, const BuildOptions& options);

    /** Wraps an already prepared sample as a single zone rooted at `rootMidi` (tests, drums-as-melodic). */
    static std::shared_ptr<const StemSound> fromPreparedSample (juce::AudioBuffer<float> sample, double sampleRate,
                                                                int rootMidi, const core::Adsr& adsr,
                                                                const juce::String& name = {});

    //==============================================================================
    const juce::String& getName() const noexcept { return name; }
    double getSampleRate() const noexcept { return sampleRate; }
    int getNumChannels() const noexcept { return numChannels; }
    /** The MIDI note at which the base sample plays at ratio 1.0 (= BuildOptions::targetRootMidi). */
    int getRootMidi() const noexcept { return rootMidi; }
    /** The stem's detected root before transposition (`StemInfo::rootMidi`). */
    int getSourceRootMidi() const noexcept { return sourceRootMidi; }
    /** Semitones applied offline: rootMidi - sourceRootMidi. */
    int getTransposition() const noexcept { return rootMidi - sourceRootMidi; }
    const core::Adsr& getAdsr() const noexcept { return adsr; }

    /** The trimmed, transposed base sample (the zone rooted at getRootMidi()). */
    const juce::AudioBuffer<float>& getSample() const noexcept { return sample; }
    int getLengthInSamples() const noexcept { return sample.getNumSamples(); }
    double getLengthInSeconds() const noexcept;

    /** The zone whose range contains `midiNote`, or nullptr when out of range. Lock-free. */
    const KeyZone* zoneForNote (int midiNote) const noexcept;
    /** 2^((midiNote - zone.zoneRootMidi) / 12). */
    static double playbackRatioFor (int midiNote, const KeyZone& zone) noexcept;
    const std::vector<KeyZone>& getZones() const noexcept { return zones; }

private:
    StemSound() = default;

    juce::String name;
    double sampleRate = 44100.0;
    int numChannels = 2;
    int rootMidi = 48;
    int sourceRootMidi = 48;
    core::Adsr adsr;
    juce::AudioBuffer<float> sample;
    std::vector<KeyZone> zones;
};

} // namespace snapplay::engine
