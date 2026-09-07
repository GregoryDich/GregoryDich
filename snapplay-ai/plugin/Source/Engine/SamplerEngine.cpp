#include "Engine/SamplerEngine.h"

namespace snapplay::engine
{

/** Worker-thread job wrapping one load; the result is handed to the message thread. */
class SamplerEngine::LoadJob final : public juce::ThreadPoolJob
{
public:
    LoadJob (SamplerEngine& ownerToUse, int generationToUse,
             std::function<std::pair<bool, juce::String> (int)> workToRun, LoadCallback onDoneToCall)
        : juce::ThreadPoolJob ("SnapPlay Load"),
          owner (ownerToUse),
          generation (generationToUse),
          work (std::move (workToRun)),
          onDone (std::move (onDoneToCall))
    {
    }

    JobStatus runJob() override
    {
        auto outcome = work (generation);
        owner.loadsInFlight.fetch_sub (1, std::memory_order_acq_rel);

        if (onDone != nullptr)
            juce::MessageManager::callAsync ([callback = std::move (onDone), outcome]
                                             {
                                                 callback (outcome.first, outcome.second);
                                             });

        return jobHasFinished;
    }

private:
    SamplerEngine& owner;
    int generation;
    std::function<std::pair<bool, juce::String> (int)> work;
    LoadCallback onDone;
};

//==============================================================================
SamplerEngine::SamplerEngine()
    : activeSound (new ActiveSound()),
      loadPool (juce::ThreadPoolOptions{}.withThreadName ("SnapPlay Sampler").withNumberOfThreads (1))
{
    synth.addSound (activeSound);

    for (int i = 0; i < numVoices; ++i)
        synth.addVoice (new StemVoice (voiceParameters));
}

SamplerEngine::~SamplerEngine()
{
    loadGeneration.fetch_add (1, std::memory_order_acq_rel);
    loadPool.removeAllJobs (true, 10000);
}

//==============================================================================
void SamplerEngine::prepare (double sampleRate, int maximumBlockSize)
{
    currentSampleRate = sampleRate;
    currentBlockSize = maximumBlockSize;
    synth.setCurrentPlaybackSampleRate (sampleRate);

    for (int i = 0; i < synth.getNumVoices(); ++i)
        if (auto* voice = dynamic_cast<StemVoice*> (synth.getVoice (i)))
            voice->prepare (sampleRate, maximumBlockSize);
}

void SamplerEngine::releaseResources()
{
}

void SamplerEngine::process (juce::AudioBuffer<float>& output, const juce::MidiBuffer& midi)
{
    output.clear();
    synth.renderNextBlock (output, midi, 0, output.getNumSamples());
}

//==============================================================================
void SamplerEngine::loadStem (const juce::File& wavFile, const cloud::StemInfo& info,
                              const StemSound::BuildOptions& options, LoadCallback onDone)
{
    juce::ignoreUnused (wavFile, info, options, onDone);
}

void SamplerEngine::loadDrumKit (const juce::File& wavFile, const cloud::StemInfo& info, LoadCallback onDone)
{
    juce::ignoreUnused (wavFile, info, onDone);
}

void SamplerEngine::installStem (std::shared_ptr<const StemSound> sound)
{
    installStemInternal (std::move (sound));
}

void SamplerEngine::installDrumKit (std::shared_ptr<const DrumKit> kit)
{
    installDrumKitInternal (std::move (kit));
}

void SamplerEngine::clear()
{
    allNotesOff();
    installStemInternal (nullptr);
    installDrumKitInternal (nullptr);
}

std::shared_ptr<const StemSound> SamplerEngine::getCurrentStem() const noexcept
{
    return activeSound->getStem();
}

std::shared_ptr<const DrumKit> SamplerEngine::getCurrentDrumKit() const noexcept
{
    return activeSound->getDrumKit();
}

//==============================================================================
void SamplerEngine::setDrumMode (bool shouldUseDrumKit) noexcept
{
    voiceParameters.drumMode.store (shouldUseDrumKit, std::memory_order_relaxed);
}

void SamplerEngine::setAdsr (const core::Adsr& adsr) noexcept
{
    voiceParameters.attackMs.store (static_cast<float> (adsr.attackMs), std::memory_order_relaxed);
    voiceParameters.decayMs.store (static_cast<float> (adsr.decayMs), std::memory_order_relaxed);
    voiceParameters.sustain.store (static_cast<float> (adsr.sustain), std::memory_order_relaxed);
    voiceParameters.releaseMs.store (static_cast<float> (adsr.releaseMs), std::memory_order_relaxed);
}

void SamplerEngine::setFilter (float cutoffHz, float resonance) noexcept
{
    voiceParameters.cutoffHz.store (cutoffHz, std::memory_order_relaxed);
    voiceParameters.resonance.store (resonance, std::memory_order_relaxed);
}

void SamplerEngine::setGain (float linearGain) noexcept
{
    voiceParameters.gain.store (linearGain, std::memory_order_relaxed);
}

void SamplerEngine::allNotesOff()
{
    for (int channel = 1; channel <= 16; ++channel)
        synth.allNotesOff (channel, true);
}

//==============================================================================
void SamplerEngine::startLoad (std::function<std::pair<bool, juce::String> (int)> work, LoadCallback onDone)
{
    const int generation = loadGeneration.fetch_add (1, std::memory_order_acq_rel) + 1;
    loadsInFlight.fetch_add (1, std::memory_order_acq_rel);
    loadPool.addJob (new LoadJob (*this, generation, std::move (work), std::move (onDone)), true);
}

void SamplerEngine::installStemInternal (std::shared_ptr<const StemSound> sound)
{
    retiredStem = activeSound->getStem();
    activeSound->setStem (std::move (sound));
}

void SamplerEngine::installDrumKitInternal (std::shared_ptr<const DrumKit> kit)
{
    retiredKit = activeSound->getDrumKit();
    activeSound->setDrumKit (std::move (kit));
}

} // namespace snapplay::engine
