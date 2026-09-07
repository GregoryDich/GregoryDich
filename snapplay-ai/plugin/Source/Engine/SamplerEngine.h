#pragma once

/**
 * The instrument: a 16-voice juce::Synthesiser playing the current StemSound (melodic
 * stems) or DrumKit (drum mode), with loading and preparation done on a private worker
 * thread and a realtime-safe install (see StemVoice.h for the handoff design).
 *
 * process() is the only audio-thread entry point; every other method is for the message
 * thread unless stated. Parameter setters store atomics and may be called from any thread.
 */

#include <JuceHeader.h>

#include "Cloud/Models.h"
#include "Core/Types.h"
#include "Engine/DrumKit.h"
#include "Engine/StemSound.h"
#include "Engine/StemVoice.h"

#include <atomic>
#include <functional>
#include <memory>

namespace snapplay::engine
{

class SamplerEngine
{
public:
    static constexpr int numVoices = 16;

    /** Delivered on the message thread when a load finishes. */
    using LoadCallback = std::function<void (bool ok, const juce::String& errorMessage)>;

    SamplerEngine();
    /** Cancels pending loads and waits for the worker thread. */
    ~SamplerEngine();

    //==============================================================================
    /** Audio-thread lifecycle: allocates voice scratch buffers. */
    void prepare (double sampleRate, int maximumBlockSize);
    void releaseResources();
    /** Renders the synthesiser into `output` (replacing its contents). Realtime-safe. */
    void process (juce::AudioBuffer<float>& output, const juce::MidiBuffer& midi);
    double getSampleRate() const noexcept { return currentSampleRate; }

    //==============================================================================
    /** Decodes `wavFile`, builds a StemSound (StemSound::build) on the worker thread and
        installs it. A newer load supersedes an older one whose result is then discarded. */
    void loadStem (const juce::File& wavFile, const cloud::StemInfo& info,
                   const StemSound::BuildOptions& options, LoadCallback onDone = {});
    /** Decodes `wavFile` and builds a DrumKit from `info.slices`, or from
        `info.transientsSeconds` / local detection when no slices were sent. */
    void loadDrumKit (const juce::File& wavFile, const cloud::StemInfo& info, LoadCallback onDone = {});
    /** Installs a prebuilt sound immediately (message thread). nullptr clears. */
    void installStem (std::shared_ptr<const StemSound> sound);
    void installDrumKit (std::shared_ptr<const DrumKit> kit);
    /** Removes both sounds and silences all voices. */
    void clear();
    bool isLoading() const noexcept { return loadsInFlight.load (std::memory_order_acquire) > 0; }
    std::shared_ptr<const StemSound> getCurrentStem() const noexcept;
    std::shared_ptr<const DrumKit> getCurrentDrumKit() const noexcept;

    //==============================================================================
    /** Selects DrumKit pads (true) or StemSound zones (false) for new notes. */
    void setDrumMode (bool shouldUseDrumKit) noexcept;
    bool isDrumMode() const noexcept { return voiceParameters.drumMode.load (std::memory_order_relaxed); }
    void setAdsr (const core::Adsr& adsr) noexcept;
    void setFilter (float cutoffHz, float resonance) noexcept;
    /** Linear gain. */
    void setGain (float linearGain) noexcept;
    VoiceParameters& getVoiceParameters() noexcept { return voiceParameters; }
    /** Message thread: releases every voice with tail-off. */
    void allNotesOff();

private:
    class LoadJob;

    /** Runs `work` on the worker thread tagged with the current load generation. */
    void startLoad (std::function<std::pair<bool, juce::String> (int generation)> work, LoadCallback onDone);
    /** Worker thread: true when a newer load started or the pool is shutting down. */
    bool isLoadSuperseded (int generation) const noexcept;
    /** Message thread: swaps a sound into ActiveSound and parks the previous one. */
    void installStemInternal (std::shared_ptr<const StemSound> sound);
    void installDrumKitInternal (std::shared_ptr<const DrumKit> kit);

    juce::Synthesiser synth;
    ActiveSound::Ptr activeSound;
    VoiceParameters voiceParameters;
    juce::ThreadPool loadPool;
    std::atomic<int> loadGeneration { 0 };
    std::atomic<int> loadsInFlight { 0 };

    /** Previously installed sounds, kept until the next install so their last reference is
        released on the message thread, never on the audio thread. */
    std::shared_ptr<const StemSound> retiredStem;
    std::shared_ptr<const DrumKit> retiredKit;

    double currentSampleRate = 44100.0;
    int currentBlockSize = 512;

    JUCE_DECLARE_WEAK_REFERENCEABLE (SamplerEngine)
    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR (SamplerEngine)
};

} // namespace snapplay::engine
