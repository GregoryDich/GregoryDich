#pragma once

/**
 * Realtime playback: the voice parameters shared by all voices, the single
 * juce::SynthesiserSound registered with the synthesiser (ActiveSound) and the voice.
 *
 * Handoff design: the synthesiser's sound list never changes after construction. Loading
 * publishes a new StemSound / DrumKit into ActiveSound with an atomic shared_ptr store;
 * voices take a shared_ptr copy at note-on (atomic load, no allocation) and drop it at
 * note-off. SamplerEngine keeps the previously installed sound alive until the next
 * install so the final reference is never released on the audio thread.
 */

#include <JuceHeader.h>

#include "Engine/DrumKit.h"
#include "Engine/StemSound.h"

#include <atomic>
#include <memory>

namespace snapplay::engine
{

/** Parameters written by the message thread and read per block by every voice. */
struct VoiceParameters
{
    std::atomic<float> attackMs { 2.0f };
    std::atomic<float> decayMs { 120.0f };
    std::atomic<float> sustain { 0.8f };          ///< 0..1
    std::atomic<float> releaseMs { 180.0f };
    std::atomic<float> cutoffHz { 20000.0f };
    std::atomic<float> resonance { 0.7071f };     ///< SVF Q
    std::atomic<float> gain { 1.0f };             ///< linear
    std::atomic<bool> drumMode { false };         ///< true → DrumKit pads, false → StemSound zones

    VoiceParameters() = default;
    JUCE_DECLARE_NON_COPYABLE (VoiceParameters)
};

/** The one sound the synthesiser owns. Applies to every note and channel; the voice
    decides whether the installed stem/kit has anything for the note. */
class ActiveSound final : public juce::SynthesiserSound
{
public:
    using Ptr = juce::ReferenceCountedObjectPtr<ActiveSound>;

    ActiveSound() = default;

    bool appliesToNote (int midiNoteNumber) override;
    bool appliesToChannel (int midiChannel) override;

    /** Message thread: publish a new stem (nullptr clears). */
    void setStem (std::shared_ptr<const StemSound> stem);
    void setDrumKit (std::shared_ptr<const DrumKit> kit);

    /** Audio thread: atomic loads, never allocate. */
    std::shared_ptr<const StemSound> getStem() const noexcept;
    std::shared_ptr<const DrumKit> getDrumKit() const noexcept;

private:
    std::atomic<std::shared_ptr<const StemSound>> stem;
    std::atomic<std::shared_ptr<const DrumKit>> drumKit;

    JUCE_DECLARE_NON_COPYABLE (ActiveSound)
};

/** One polyphonic voice: varispeed sample playback through a Lagrange interpolator,
    juce::ADSR amplitude envelope and a TPT state-variable low-pass filter. All methods
    except prepare() run on the audio thread and are allocation-free. */
class StemVoice final : public juce::SynthesiserVoice
{
public:
    explicit StemVoice (const VoiceParameters& parameters);

    /** Allocates the scratch buffer and prepares the filter; call before playback. */
    void prepare (double sampleRate, int maximumBlockSize);

    bool canPlaySound (juce::SynthesiserSound* sound) override;
    void startNote (int midiNoteNumber, float velocity, juce::SynthesiserSound* sound, int currentPitchWheelPosition) override;
    void stopNote (float velocity, bool allowTailOff) override;
    void pitchWheelMoved (int newPitchWheelValue) override;
    void controllerMoved (int controllerNumber, int newControllerValue) override;
    void renderNextBlock (juce::AudioBuffer<float>& outputBuffer, int startSample, int numSamples) override;
    void setCurrentPlaybackSampleRate (double newRate) override;

    /** Pitch-bend range applied to the wheel, in semitones (default 2). */
    void setPitchBendRange (float semitones) noexcept { pitchBendRange = semitones; }

private:
    void updateEnvelopeParameters();
    void updateFilterParameters();

    const VoiceParameters& params;

    std::shared_ptr<const StemSound> stem;
    std::shared_ptr<const DrumKit> kit;
    const StemSound::KeyZone* zone = nullptr;
    const DrumKit::Pad* pad = nullptr;
    const juce::AudioBuffer<float>* source = nullptr;   ///< zone or pad audio being played

    double sourceSampleRate = 44100.0;
    double baseRatio = 1.0;          ///< from the note and zone root
    double pitchWheelRatio = 1.0;    ///< from the wheel and bend range
    double position = 0.0;           ///< read head in source samples
    float noteGain = 1.0f;           ///< velocity
    float pitchBendRange = 2.0f;

    juce::LagrangeInterpolator interpolators[2];
    juce::ADSR envelope;
    juce::dsp::StateVariableTPTFilter<float> filter;
    juce::AudioBuffer<float> scratch;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR (StemVoice)
};

} // namespace snapplay::engine
