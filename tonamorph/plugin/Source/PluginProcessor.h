#pragma once

/**
 * Tonamorph — the plugin. Owns the parameter tree, the cloud session (ApiClient,
 * AuthManager, JobClient), the sampler engine, the Scale-Snap MIDI processor, the
 * current JobResult and the on-screen keyboard state.
 *
 * Threading: processBlock() touches only the engine, the scale processor and cached
 * atomic parameter pointers. Everything else runs on the message thread. Parameter
 * changes reach the engine through atomics, so host automation is realtime-safe; the
 * few reactions that need the message thread (Scale-Snap model, stem reloads, cached-job
 * restore) are flagged and delivered through an AsyncUpdater.
 */

#include <JuceHeader.h>

#include "Cloud/ApiClient.h"
#include "Cloud/AuthManager.h"
#include "Cloud/JobClient.h"
#include "Cloud/Models.h"
#include "Core/Types.h"
#include "Engine/SamplerEngine.h"
#include "Engine/ScaleLockProcessor.h"

#include <atomic>
#include <optional>

namespace tonamorph
{

/** Parameter IDs (contract-fixed; used by the editor attachments and state files). */
namespace ParamIds
{
    inline constexpr const char* attack     = "attack";       ///< float, ms, 1..2000, default 2
    inline constexpr const char* decay      = "decay";        ///< float, ms, 1..4000, default 120
    inline constexpr const char* sustain    = "sustain";      ///< float, 0..1, default 0.8
    inline constexpr const char* release    = "release";      ///< float, ms, 5..5000, default 180
    inline constexpr const char* cutoff     = "cutoff";       ///< float, Hz, 20..20000, default 20000
    inline constexpr const char* resonance  = "resonance";    ///< float, Q, 0.1..10, default 0.7071
    inline constexpr const char* gain       = "gain";         ///< float, dB, -60..+12, default 0
    inline constexpr const char* category   = "category";     ///< choice Bass/Drums/Synth/Vocals, default Bass
    inline constexpr const char* rootTarget = "rootTarget";   ///< int 24..84, default 48
    inline constexpr const char* drumMode   = "drumMode";     ///< bool, default false
    inline constexpr const char* scaleMode  = "scaleMode";    ///< choice, core::ScaleMode order, default Detected
    inline constexpr const char* scaleRoot  = "scaleRoot";    ///< int 0..11, default 0 (set from analysis.key on load)
}

class TonamorphAudioProcessor final : public juce::AudioProcessor,
                                     private juce::AudioProcessorValueTreeState::Listener,
                                     private juce::ChangeListener,
                                     private cloud::AuthManager::Listener,
                                     private juce::AsyncUpdater,
                                     private juce::Timer
{
public:
    /** Index order of the `category` choice parameter. */
    enum class Category { Bass = 0, Drums, Synth, Vocals };
    static constexpr int numCategories = 4;

    /** Identifier of the APVTS root tree and of the saved state XML element. */
    static constexpr const char* stateTreeType = "Tonamorph";
    /** Property on the state tree holding the last job id, so a cached job reloads
        without spending a credit. */
    static constexpr const char* lastJobIdProperty = "lastJobId";

    TonamorphAudioProcessor();
    ~TonamorphAudioProcessor() override;

    //==============================================================================
    static juce::AudioProcessorValueTreeState::ParameterLayout createParameterLayout();
    /** "Bass", "Drums", "Synth", "Vocals". */
    static const juce::StringArray& getCategoryLabels();
    /** "Detected", "Major", "Minor", "PentatonicMajor", "PentatonicMinor", "Off". */
    static const juce::StringArray& getScaleModeLabels();
    /** Contract stem name for a category index: bass, drums, other, vocals. */
    static juce::String stemNameForCategory (int categoryIndex);

    //==============================================================================
    void prepareToPlay (double sampleRate, int samplesPerBlock) override;
    void releaseResources() override;
    bool isBusesLayoutSupported (const BusesLayout& layouts) const override;
    void processBlock (juce::AudioBuffer<float>& buffer, juce::MidiBuffer& midiMessages) override;
    /** Keeps the inherited double-precision overload visible; the plugin only ever runs in
        single precision (supportsDoublePrecisionProcessing() is false). */
    using juce::AudioProcessor::processBlock;

    juce::AudioProcessorEditor* createEditor() override;
    bool hasEditor() const override { return true; }

    const juce::String getName() const override { return JucePlugin_Name; }
    bool acceptsMidi() const override { return true; }
    bool producesMidi() const override { return false; }
    bool isMidiEffect() const override { return false; }
    double getTailLengthSeconds() const override;

    int getNumPrograms() override { return 1; }
    int getCurrentProgram() override { return 0; }
    void setCurrentProgram (int index) override { juce::ignoreUnused (index); }
    const juce::String getProgramName (int index) override { juce::ignoreUnused (index); return {}; }
    void changeProgramName (int index, const juce::String& newName) override { juce::ignoreUnused (index, newName); }

    /** Serialises the parameter tree plus `lastJobIdProperty`. */
    void getStateInformation (juce::MemoryBlock& destData) override;
    /** Restores parameters and, when a last job id is present, reloads it from the cache
        (JobClient::loadCachedJob) without a credit charge. */
    void setStateInformation (const void* data, int sizeInBytes) override;

    //==============================================================================
    juce::AudioProcessorValueTreeState& getValueTreeState() noexcept { return apvts; }
    engine::SamplerEngine& getEngine() noexcept { return engine; }
    engine::ScaleLockProcessor& getScaleLock() noexcept { return scaleLock; }
    cloud::ApiClient& getApiClient() noexcept { return apiClient; }
    cloud::AuthManager& getAuthManager() noexcept { return authManager; }
    cloud::JobClient& getJobClient() noexcept { return jobClient; }
    juce::MidiKeyboardState& getKeyboardState() noexcept { return keyboardState; }

    /** The result of the current/last job, if any (message thread). */
    const std::optional<cloud::JobResult>& getCurrentResult() const noexcept { return currentResult; }
    /** Thread-safe: hosts may serialise state off the message thread. */
    juce::String getLastJobId() const;
    std::optional<cloud::KeyInfo> getDetectedKey() const;
    std::optional<double> getDetectedBpm() const;

    /** Builds JobOptions from the current parameters (target root, drum slices on, all
        stems, transcribe bass/other/vocals) and a fresh idempotency key. */
    cloud::JobOptions makeJobOptions() const;
    /** Submits an audio file through the JobClient (checks credits first). */
    void submitAudioFile (const juce::File& audioFile);
    int getSelectedCategory() const;
    bool isDrumMode() const;
    /** (Re)loads the stem for the current category / root target / drum mode into the
        engine from the job cache and applies Auto-ADSR. No-op without a ready result. */
    void loadSelectedStem();

private:
    void parameterChanged (const juce::String& parameterID, float newValue) override;
    void changeListenerCallback (juce::ChangeBroadcaster* source) override;
    void authStateChanged (cloud::AuthManager&) override;
    void balanceChanged (cloud::AuthManager&, const cloud::CreditBalance& balance) override;
    void handleAsyncUpdate() override;
    void timerCallback() override;

    /** Called when the JobClient reaches Ready: stores the result, installs the detected
        scale and root, loads the selected stem. */
    void onJobReady (const cloud::JobResult& result);
    void applyScaleParametersToProcessor();

    /** Pushes every parameter into the engine atomics (constructor / state restore). */
    void syncEngineFromParameters();
    /** Drum pads are used only while the Drums category is selected with drum mode on. */
    void syncDrumModeToEngine();
    /** Any thread: asks the message thread for a debounced loadSelectedStem(). */
    void requestStemReload();
    /** Message thread: reloads `jobId` from the JobClient cache when the directory exists. */
    void restoreCachedJob (const juce::String& jobIdToRestore);
    void setScaleRootParameter (int pitchClass);
    void applyAdsr (const core::Adsr& adsr);
    /** loadSelectedStem() with the Auto-ADSR step optional (skipped on state restore so the
        saved envelope survives). */
    void reloadStem (bool applyAutoAdsr);

    static constexpr int stemReloadDebounceMs = 250;

    juce::AudioProcessorValueTreeState apvts;

    std::atomic<float>* attackParam = nullptr;
    std::atomic<float>* decayParam = nullptr;
    std::atomic<float>* sustainParam = nullptr;
    std::atomic<float>* releaseParam = nullptr;
    std::atomic<float>* cutoffParam = nullptr;
    std::atomic<float>* resonanceParam = nullptr;
    std::atomic<float>* gainParam = nullptr;
    std::atomic<float>* categoryParam = nullptr;
    std::atomic<float>* rootTargetParam = nullptr;
    std::atomic<float>* drumModeParam = nullptr;
    std::atomic<float>* scaleModeParam = nullptr;
    std::atomic<float>* scaleRootParam = nullptr;

    cloud::ApiClient apiClient;
    cloud::AuthManager authManager;
    cloud::JobClient jobClient;
    engine::SamplerEngine engine;
    engine::ScaleLockProcessor scaleLock;
    juce::MidiKeyboardState keyboardState;

    std::optional<cloud::JobResult> currentResult;
    juce::String lastJobId;

    std::atomic<bool> scaleParametersDirty { false };
    std::atomic<bool> stemReloadPending { false };
    bool restoringCachedJob = false;
    int stemLoadSerial = 0;

    /** Guards lastJobId / pendingRestoreJobId, which state calls may touch off the message thread. */
    mutable juce::CriticalSection stateLock;
    juce::String pendingRestoreJobId;

    JUCE_DECLARE_WEAK_REFERENCEABLE (TonamorphAudioProcessor)
    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR (TonamorphAudioProcessor)
};

} // namespace tonamorph
