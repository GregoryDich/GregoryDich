#include "Engine/StemVoice.h"

#include <cmath>

namespace tonamorph::engine
{

namespace
{
    constexpr double filterSmoothingSeconds = 0.02;
    constexpr float minCutoffHz = 20.0f;
    constexpr float minResonance = 0.05f;

    /** Gentle concave velocity curve: unity at full velocity, -2.5 dB at half. */
    float velocityToGain (float velocity) noexcept
    {
        const float v = juce::jlimit (0.0f, 1.0f, velocity);
        return v * (2.0f - v);
    }

    double pitchWheelToRatio (int wheelPosition, float bendRangeSemitones) noexcept
    {
        const double bend = static_cast<double> (juce::jlimit (0, 16383, wheelPosition) - 8192) / 8192.0;
        return std::pow (2.0, bend * static_cast<double> (bendRangeSemitones) / 12.0);
    }
} // namespace

//==============================================================================
bool ActiveSound::appliesToNote (int midiNoteNumber)
{
    juce::ignoreUnused (midiNoteNumber);
    return true;
}

bool ActiveSound::appliesToChannel (int midiChannel)
{
    juce::ignoreUnused (midiChannel);
    return true;
}

void ActiveSound::setStem (std::shared_ptr<const StemSound> newStem)
{
    stem.store (std::move (newStem), std::memory_order_release);
}

void ActiveSound::setDrumKit (std::shared_ptr<const DrumKit> newKit)
{
    drumKit.store (std::move (newKit), std::memory_order_release);
}

std::shared_ptr<const StemSound> ActiveSound::getStem() const noexcept
{
    return stem.load (std::memory_order_acquire);
}

std::shared_ptr<const DrumKit> ActiveSound::getDrumKit() const noexcept
{
    return drumKit.load (std::memory_order_acquire);
}

//==============================================================================
StemVoice::StemVoice (const VoiceParameters& parameters)
    : params (parameters)
{
}

void StemVoice::prepare (double sampleRate, int maximumBlockSize)
{
    const int blockSize = juce::jmax (1, maximumBlockSize);

    scratch.setSize (2, blockSize, false, false, true);
    scratch.clear();

    juce::dsp::ProcessSpec spec { sampleRate, static_cast<juce::uint32> (blockSize), 2 };
    filter.prepare (spec);
    filter.setType (juce::dsp::StateVariableTPTFilterType::lowpass);

    setCurrentPlaybackSampleRate (sampleRate);
    stopPlayback();
}

bool StemVoice::canPlaySound (juce::SynthesiserSound* sound)
{
    return dynamic_cast<ActiveSound*> (sound) != nullptr;
}

void StemVoice::startNote (int midiNoteNumber, float velocity, juce::SynthesiserSound* sound, int currentPitchWheelPosition)
{
    source = nullptr;
    zone = nullptr;
    pad = nullptr;

    auto* activeSound = dynamic_cast<ActiveSound*> (sound);
    const double voiceRate = getSampleRate();

    if (activeSound == nullptr || voiceRate <= 0.0 || scratch.getNumSamples() <= 0)
    {
        stopPlayback();
        return;
    }

    const bool drum = params.drumMode.load (std::memory_order_relaxed);

    if (drum)
    {
        stem.reset();
        kit = activeSound->getDrumKit();
        pad = kit != nullptr ? kit->padForNote (midiNoteNumber) : nullptr;

        if (pad != nullptr)
        {
            source = &pad->audio;
            sourceSampleRate = kit->getSampleRate();
            baseRatio = 1.0;
        }
    }
    else
    {
        kit.reset();
        stem = activeSound->getStem();
        zone = stem != nullptr ? stem->zoneForNote (midiNoteNumber) : nullptr;

        if (zone != nullptr)
        {
            source = &zone->audio;
            sourceSampleRate = stem->getSampleRate();
            baseRatio = StemSound::playbackRatioFor (midiNoteNumber, *zone);
        }
    }

    if (source == nullptr || source->getNumSamples() <= 0 || source->getNumChannels() <= 0 || sourceSampleRate <= 0.0)
    {
        stopPlayback();
        return;
    }

    oneShot = drum;
    baseRatio *= sourceSampleRate / voiceRate;
    pitchWheelRatio = pitchWheelToRatio (currentPitchWheelPosition, pitchBendRange);
    position = 0.0;
    noteGain = velocityToGain (velocity);

    for (auto& interpolator : interpolators)
        interpolator.reset();

    updateEnvelopeParameters();
    envelope.reset();
    envelope.noteOn();

    updateFilterParameters();
    cutoffSmoothed.setCurrentAndTargetValue (cutoffSmoothed.getTargetValue());
    resonanceSmoothed.setCurrentAndTargetValue (resonanceSmoothed.getTargetValue());
    filter.reset();
    filter.setCutoffFrequency (cutoffSmoothed.getCurrentValue());
    filter.setResonance (resonanceSmoothed.getCurrentValue());
}

void StemVoice::stopNote (float velocity, bool allowTailOff)
{
    juce::ignoreUnused (velocity);

    if (! allowTailOff)
    {
        stopPlayback();   // choke / voice stealing
        return;
    }

    if (oneShot)
        return;           // drum pads play to their end regardless of the key

    envelope.noteOff();
}

void StemVoice::pitchWheelMoved (int newPitchWheelValue)
{
    pitchWheelRatio = pitchWheelToRatio (newPitchWheelValue, pitchBendRange);
}

void StemVoice::controllerMoved (int controllerNumber, int newControllerValue)
{
    juce::ignoreUnused (controllerNumber, newControllerValue);
}

void StemVoice::renderNextBlock (juce::AudioBuffer<float>& outputBuffer, int startSample, int numSamples)
{
    if (source == nullptr || numSamples <= 0)
        return;

    const int scratchSize = scratch.getNumSamples();

    if (scratchSize <= 0 || ! envelope.isActive())
    {
        stopPlayback();
        return;
    }

    updateEnvelopeParameters();
    updateFilterParameters();

    const int sourceLength = source->getNumSamples();
    const int sourceChannels = juce::jmin (2, source->getNumChannels());
    const int outputChannels = outputBuffer.getNumChannels();
    const double ratio = baseRatio * pitchWheelRatio;
    const float gain = noteGain * params.gain.load (std::memory_order_relaxed);

    int rendered = 0;
    bool finished = false;

    while (rendered < numSamples && ! finished)
    {
        const int chunk = juce::jmin (scratchSize, numSamples - rendered);
        const auto readPosition = static_cast<int> (position);
        const int available = sourceLength - readPosition;

        if (available <= 0)
        {
            finished = true;
            break;
        }

        int used = 0;

        for (int channel = 0; channel < sourceChannels; ++channel)
            used = interpolators[channel].process (ratio, source->getReadPointer (channel, readPosition),
                                                   scratch.getWritePointer (channel), chunk, available, 0);

        position = static_cast<double> (readPosition + used);

        const bool smoothing = cutoffSmoothed.isSmoothing() || resonanceSmoothed.isSmoothing();
        float* const channelData[2] = { scratch.getWritePointer (0),
                                        sourceChannels > 1 ? scratch.getWritePointer (1) : nullptr };

        for (int i = 0; i < chunk; ++i)
        {
            const float envelopeGain = envelope.getNextSample();

            if (smoothing)
            {
                filter.setCutoffFrequency (cutoffSmoothed.getNextValue());
                filter.setResonance (resonanceSmoothed.getNextValue());
            }

            for (int channel = 0; channel < sourceChannels; ++channel)
            {
                auto* samples = channelData[channel];
                samples[i] = filter.processSample (channel, samples[i] * envelopeGain);
            }
        }

        if (outputChannels == 1 && sourceChannels == 2)
        {
            outputBuffer.addFrom (0, startSample + rendered, scratch, 0, 0, chunk, gain * 0.5f);
            outputBuffer.addFrom (0, startSample + rendered, scratch, 1, 0, chunk, gain * 0.5f);
        }
        else
        {
            for (int channel = 0; channel < outputChannels; ++channel)
                outputBuffer.addFrom (channel, startSample + rendered, scratch,
                                      juce::jmin (channel, sourceChannels - 1), 0, chunk, gain);
        }

        rendered += chunk;

        if (! envelope.isActive() || position >= static_cast<double> (sourceLength))
            finished = true;
    }

    if (finished)
        stopPlayback();
}

void StemVoice::setCurrentPlaybackSampleRate (double newRate)
{
    juce::SynthesiserVoice::setCurrentPlaybackSampleRate (newRate);

    if (newRate > 0.0)
    {
        envelope.setSampleRate (newRate);
        cutoffSmoothed.reset (newRate, filterSmoothingSeconds);
        resonanceSmoothed.reset (newRate, filterSmoothingSeconds);
        updateEnvelopeParameters();
    }
}

void StemVoice::updateEnvelopeParameters()
{
    juce::ADSR::Parameters parameters;
    parameters.attack  = juce::jmax (0.0f, params.attackMs.load (std::memory_order_relaxed)) * 0.001f;
    parameters.decay   = juce::jmax (0.0f, params.decayMs.load (std::memory_order_relaxed)) * 0.001f;
    parameters.sustain = juce::jlimit (0.0f, 1.0f, params.sustain.load (std::memory_order_relaxed));
    parameters.release = juce::jmax (0.0f, params.releaseMs.load (std::memory_order_relaxed)) * 0.001f;
    envelope.setParameters (parameters);
}

void StemVoice::updateFilterParameters()
{
    const double voiceRate = getSampleRate();
    const auto maxCutoffHz = static_cast<float> (voiceRate > 0.0 ? voiceRate * 0.49 : 20000.0);

    cutoffSmoothed.setTargetValue (juce::jlimit (minCutoffHz, juce::jmax (minCutoffHz, maxCutoffHz),
                                                 params.cutoffHz.load (std::memory_order_relaxed)));
    resonanceSmoothed.setTargetValue (juce::jmax (minResonance, params.resonance.load (std::memory_order_relaxed)));
}

void StemVoice::stopPlayback() noexcept
{
    source = nullptr;
    zone = nullptr;
    pad = nullptr;
    stem.reset();
    kit.reset();
    oneShot = false;
    envelope.reset();
    clearCurrentNote();
}

} // namespace tonamorph::engine
