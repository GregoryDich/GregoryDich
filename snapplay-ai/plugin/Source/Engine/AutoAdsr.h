#pragma once

/**
 * Auto-ADSR (contract §8): use the server's `suggested_adsr` when present, otherwise
 * derive one from the stem's envelope, and push the result into the plugin parameters.
 */

#include <JuceHeader.h>

#include "Cloud/Models.h"
#include "Core/Envelope.h"
#include "Core/Types.h"

#include <algorithm>

namespace snapplay::engine
{

/** `info.suggestedAdsr` when present, else core::deriveAdsr on the given mono signal. */
inline core::Adsr resolveAdsr (const cloud::StemInfo& info, const float* mono, int numSamples, double sampleRate)
{
    if (info.suggestedAdsr.has_value())
        return *info.suggestedAdsr;

    return core::deriveAdsr (mono, numSamples, sampleRate);
}

/** Same as above for a multi-channel buffer: channels are averaged into a temporary
    mono buffer first. Not for the audio thread (allocates). */
inline core::Adsr resolveAdsr (const cloud::StemInfo& info, const juce::AudioBuffer<float>& audio, double sampleRate)
{
    if (info.suggestedAdsr.has_value())
        return *info.suggestedAdsr;

    const int numSamples = audio.getNumSamples();
    const int numChannels = audio.getNumChannels();

    if (numSamples <= 0 || numChannels <= 0)
        return {};

    juce::AudioBuffer<float> mono (1, numSamples);
    mono.clear();

    for (int channel = 0; channel < numChannels; ++channel)
        mono.addFrom (0, 0, audio, channel, 0, numSamples, 1.0f / static_cast<float> (numChannels));

    return core::deriveAdsr (mono.getReadPointer (0), numSamples, sampleRate);
}

/** Writes an Adsr into the attack/decay/sustain/release parameters with host-notifying
    change gestures so automation and the editor follow. Message thread only. Values are
    clamped to each parameter's range. */
inline void applyAdsrToParameters (juce::RangedAudioParameter& attack, juce::RangedAudioParameter& decay,
                                   juce::RangedAudioParameter& sustain, juce::RangedAudioParameter& release,
                                   const core::Adsr& adsr)
{
    const auto apply = [] (juce::RangedAudioParameter& parameter, double value)
    {
        const auto& range = parameter.getNormalisableRange();
        const float clamped = std::clamp (static_cast<float> (value), range.start, range.end);

        parameter.beginChangeGesture();
        parameter.setValueNotifyingHost (parameter.convertTo0to1 (clamped));
        parameter.endChangeGesture();
    };

    apply (attack, adsr.attackMs);
    apply (decay, adsr.decayMs);
    apply (sustain, adsr.sustain);
    apply (release, adsr.releaseMs);
}

} // namespace snapplay::engine
