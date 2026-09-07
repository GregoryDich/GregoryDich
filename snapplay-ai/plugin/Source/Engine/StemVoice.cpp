#include "Engine/StemVoice.h"

namespace snapplay::engine
{

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
    juce::ignoreUnused (sampleRate, maximumBlockSize);
}

bool StemVoice::canPlaySound (juce::SynthesiserSound* sound)
{
    return dynamic_cast<ActiveSound*> (sound) != nullptr;
}

void StemVoice::startNote (int midiNoteNumber, float velocity, juce::SynthesiserSound* sound, int currentPitchWheelPosition)
{
    juce::ignoreUnused (midiNoteNumber, velocity, sound, currentPitchWheelPosition);
    clearCurrentNote();
}

void StemVoice::stopNote (float velocity, bool allowTailOff)
{
    juce::ignoreUnused (velocity, allowTailOff);
    clearCurrentNote();
}

void StemVoice::pitchWheelMoved (int newPitchWheelValue)
{
    juce::ignoreUnused (newPitchWheelValue);
}

void StemVoice::controllerMoved (int controllerNumber, int newControllerValue)
{
    juce::ignoreUnused (controllerNumber, newControllerValue);
}

void StemVoice::renderNextBlock (juce::AudioBuffer<float>& outputBuffer, int startSample, int numSamples)
{
    juce::ignoreUnused (outputBuffer, startSample, numSamples);
}

void StemVoice::setCurrentPlaybackSampleRate (double newRate)
{
    juce::SynthesiserVoice::setCurrentPlaybackSampleRate (newRate);
}

void StemVoice::updateEnvelopeParameters()
{
}

void StemVoice::updateFilterParameters()
{
}

} // namespace snapplay::engine
