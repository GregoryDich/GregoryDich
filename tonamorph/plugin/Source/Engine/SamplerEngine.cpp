#include "Engine/SamplerEngine.h"

#include "Core/Strings.h"

#include <algorithm>
#include <exception>

namespace tonamorph::engine
{

namespace
{
    constexpr int maxDrumChannels = 2;
    /** Defensive bound on decoded length; contract inputs never exceed 60 s. */
    constexpr double maxLoadSeconds = 120.0;
    const char* const supersededMessage = "Superseded by a newer load";

    /** Worker thread: decodes `file` into `audio` (at most `maxChannels` channels).
        Returns an error message, or an empty string on success. */
    juce::String readAudioFile (const juce::File& file, int maxChannels, juce::AudioBuffer<float>& audio, double& sampleRate)
    {
        juce::AudioFormatManager manager;
        manager.registerBasicFormats();

        std::unique_ptr<juce::AudioFormatReader> reader (manager.createReaderFor (file));

        if (reader == nullptr)
            return "Could not open " + file.getFileName();

        if (reader->sampleRate <= 0.0 || reader->numChannels == 0 || reader->lengthInSamples <= 0)
            return "No audio in " + file.getFileName();

        const auto maxSamples = static_cast<juce::int64> (reader->sampleRate * maxLoadSeconds);
        const auto length = static_cast<int> (juce::jmin (reader->lengthInSamples, maxSamples));
        const int channels = juce::jlimit (1, juce::jmax (1, maxChannels), static_cast<int> (reader->numChannels));

        audio.setSize (channels, length);

        if (! reader->read (&audio, 0, length, 0, true, true))
            return "Could not decode " + file.getFileName();

        sampleRate = reader->sampleRate;
        return {};
    }
} // namespace

/** Worker-thread job wrapping one load; the result is handed to the message thread. */
class SamplerEngine::LoadJob final : public juce::ThreadPoolJob
{
public:
    LoadJob (SamplerEngine& ownerToUse, int generationToUse,
             std::function<std::pair<bool, juce::String> (int)> workToRun, LoadCallback onDoneToCall)
        : juce::ThreadPoolJob (juce::String (strings::productName) + " Load"),
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
      loadPool (juce::ThreadPoolOptions{}.withThreadName (juce::String (strings::productName) + " Sampler")
                                         .withNumberOfThreads (1))
{
    synth.addSound (activeSound);

    for (int i = 0; i < numVoices; ++i)
        synth.addVoice (new StemVoice (voiceParameters));
}

SamplerEngine::~SamplerEngine()
{
    masterReference.clear();
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
    juce::WeakReference<SamplerEngine> weakSelf (this);

    startLoad ([this, weakSelf, wavFile, info, options] (int generation) -> std::pair<bool, juce::String>
    {
        juce::AudioBuffer<float> audio;
        double sampleRate = 0.0;

        if (auto error = readAudioFile (wavFile, options.maxChannels, audio, sampleRate); error.isNotEmpty())
            return { false, error };

        if (isLoadSuperseded (generation))
            return { false, supersededMessage };

        std::shared_ptr<const StemSound> sound;

        try
        {
            sound = StemSound::build (audio, sampleRate, info, options);
        }
        catch (const std::exception& e)
        {
            return { false, juce::String ("Stem preparation failed: ") + e.what() };
        }

        if (sound == nullptr)
            return { false, "Stem " + info.name + " contains no audio after trimming" };

        if (isLoadSuperseded (generation))
            return { false, supersededMessage };

        juce::MessageManager::callAsync ([weakSelf, sound, generation]
        {
            if (auto* self = weakSelf.get())
                if (self->loadGeneration.load (std::memory_order_acquire) == generation)
                    self->installStemInternal (sound);
        });

        return { true, {} };
    }, std::move (onDone));
}

void SamplerEngine::loadDrumKit (const juce::File& wavFile, const cloud::StemInfo& info, LoadCallback onDone)
{
    juce::WeakReference<SamplerEngine> weakSelf (this);

    startLoad ([this, weakSelf, wavFile, info] (int generation) -> std::pair<bool, juce::String>
    {
        juce::AudioBuffer<float> audio;
        double sampleRate = 0.0;

        if (auto error = readAudioFile (wavFile, maxDrumChannels, audio, sampleRate); error.isNotEmpty())
            return { false, error };

        if (isLoadSuperseded (generation))
            return { false, supersededMessage };

        std::shared_ptr<const DrumKit> kit;

        try
        {
            kit = info.slices.empty() ? DrumKit::buildFromTransients (audio, sampleRate, info.transientsSeconds)
                                      : DrumKit::build (audio, sampleRate, info.slices);
        }
        catch (const std::exception& e)
        {
            return { false, juce::String ("Drum kit preparation failed: ") + e.what() };
        }

        if (kit == nullptr)
            return { false, "No drum slices could be cut from " + info.name };

        if (isLoadSuperseded (generation))
            return { false, supersededMessage };

        juce::MessageManager::callAsync ([weakSelf, kit, generation]
        {
            if (auto* self = weakSelf.get())
                if (self->loadGeneration.load (std::memory_order_acquire) == generation)
                    self->installDrumKitInternal (kit);
        });

        return { true, {} };
    }, std::move (onDone));
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
bool SamplerEngine::isLoadSuperseded (int generation) const noexcept
{
    if (loadGeneration.load (std::memory_order_acquire) != generation)
        return true;

    if (auto* job = juce::ThreadPoolJob::getCurrentThreadPoolJob())
        return job->shouldExit();

    return false;
}

void SamplerEngine::startLoad (std::function<std::pair<bool, juce::String> (int)> work, LoadCallback onDone)
{
    const int generation = loadGeneration.fetch_add (1, std::memory_order_acq_rel) + 1;
    loadsInFlight.fetch_add (1, std::memory_order_acq_rel);
    loadPool.addJob (new LoadJob (*this, generation, std::move (work), std::move (onDone)), true);
}

template <typename T>
void SamplerEngine::retire (std::vector<std::shared_ptr<const T>>& retired, std::shared_ptr<const T> sound)
{
    if (sound != nullptr)
        retired.push_back (std::move (sound));

    // A retired sound is never handed out again, so the audio thread can only drop
    // references to it. use_count() == 1 therefore means this vector is the last owner and
    // the deallocation happens here, on the message thread.
    const auto unreferenced = [] (const std::shared_ptr<const T>& parked)
    {
        return parked.use_count() == 1;
    };

    retired.erase (std::remove_if (retired.begin(), retired.end(), unreferenced), retired.end());
}

void SamplerEngine::installStemInternal (std::shared_ptr<const StemSound> sound)
{
    auto previous = activeSound->getStem();
    activeSound->setStem (std::move (sound));
    retire (retiredStems, std::move (previous));
}

void SamplerEngine::installDrumKitInternal (std::shared_ptr<const DrumKit> kit)
{
    auto previous = activeSound->getDrumKit();
    activeSound->setDrumKit (std::move (kit));
    retire (retiredKits, std::move (previous));
}

} // namespace tonamorph::engine
