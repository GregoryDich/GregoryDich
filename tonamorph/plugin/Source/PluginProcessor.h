#pragma once

/**
 * The plugin. Owns the parameter tree, the settings file, the cloud session (ApiClient,
 * AuthManager, JobClient), the sampler engine, the Scale-Snap MIDI processor, the
 * current JobResult and the on-screen keyboard state.
 *
 * Threading: processBlock() touches only the engine, the scale processor, cached atomic
 * parameter pointers and one atomic flag. Everything else runs on the message thread.
 * Parameter changes reach the engine through atomics, so host automation is
 * realtime-safe; the few reactions that need the message thread (Scale-Snap model, stem
 * reloads, cached-job restore) are flagged and delivered through an AsyncUpdater.
 *
 * Result flow (ARCHITECTURE.md §5): the analysis — key, BPM, root, Scale-Snap — is applied
 * the moment the `result` event arrives (JobClient reaches Downloading), and the selected
 * stem is loaded as soon as its own download lands, before the other stems finish.
 */

#include <JuceHeader.h>

#include "App/PluginSettings.h"
#include "Cloud/ApiClient.h"
#include "Cloud/AuthManager.h"
#include "Cloud/JobClient.h"
#include "Cloud/Models.h"
#include "Core/Types.h"
#include "Engine/SamplerEngine.h"
#include "Engine/ScaleLockProcessor.h"

#include <atomic>
#include <cstdint>
#include <functional>
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

    /** Identifier of the APVTS root tree and of the saved state XML element. Pinned: saved
        projects carry it, so it must not follow strings::productName. */
    static constexpr const char* stateTreeType = "Tonamorph";   // not user-facing
    /** Property on the state tree holding the last job id, so a cached job reloads
        without spending a credit. */
    static constexpr const char* lastJobIdProperty = "lastJobId";

    /** What happened to a rating sent with submitFeedback(). */
    enum class FeedbackOutcome { Sent, Refunded, Failed };

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

    /** Serialises the parameter tree plus `lastJobIdProperty` (never the demo). */
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
    PluginSettings& getSettings() noexcept { return settings; }
    juce::MidiKeyboardState& getKeyboardState() noexcept { return keyboardState; }
    /** Fires on the message thread whenever the result state changes in a way the editor
        shows: analysis applied, a stem became playable, a rating was answered. */
    juce::ChangeBroadcaster& getResultEvents() noexcept { return resultEvents; }

    /** The result of the current/last job, if any (message thread). */
    const std::optional<cloud::JobResult>& getCurrentResult() const noexcept { return currentResult; }
    /** True once a stem of the current result is installed in the engine. */
    bool isCurrentResultPlayable() const noexcept;
    /** True when the current result came back from the host's saved state, not a fresh morph. */
    bool wasCurrentResultRestored() const noexcept { return currentResultRestored; }
    /** Thread-safe: hosts may serialise state off the message thread. */
    juce::String getLastJobId() const;
    std::optional<cloud::KeyInfo> getDetectedKey() const;
    std::optional<double> getDetectedBpm() const;
    /** Milliseconds from the drop to the first playable stem of the current job (GTM B §1
        criterion 1); nullopt for restored jobs and the demo. */
    std::optional<juce::int64> getDropToReadyMs() const noexcept { return dropToReadyMs; }

    /** Builds JobOptions from the current parameters (target root, drum slices on, all
        stems, transcribe bass/other/vocals) and a fresh idempotency key. */
    cloud::JobOptions makeJobOptions() const;
    /** Submits an audio file through the JobClient (checks credits first) and starts the
        drop-to-ready timer. */
    void submitAudioFile (const juce::File& audioFile);
    int getSelectedCategory() const;
    bool isDrumMode() const;
    /** (Re)loads the stem for the current category / root target / drum mode into the
        engine from the job cache and applies Auto-ADSR. No-op without a result; while a
        job is still downloading, a stem that has not landed yet is loaded when it does. */
    void loadSelectedStem();

    //==============================================================================
    /** Installs the bundled demo morph as the current result when nothing else is loaded
        or pending (no credit, no network). Called by the editor when it opens. */
    void loadDemoIfIdle();

    /** True for a fresh, non-demo result that has not been rated yet. */
    bool canRateCurrentResult() const;
    /** POST /v1/jobs/{id}/feedback for the current result; `onDone` runs on the message
        thread. A refund updates the balance at once. */
    void submitFeedback (bool thumbsUp, const juce::String& reason, const juce::String& note,
                         std::function<void (FeedbackOutcome)> onDone);

    /** Crash-report opt-in (PluginSettings); turning it on installs the handler. */
    void setCrashReportingEnabled (bool enabled);
    /** Uploads or expires pending crash reports once per process; called on editor open. */
    void flushCrashReports();

    /** Number of audio blocks that carried a note-on (DAW or on-screen keys); the editor
        compares snapshots to notice "a key was played since the hint appeared". */
    std::uint32_t getNoteOnCount() const noexcept { return noteOnBlocks.load (std::memory_order_relaxed); }

private:
    void parameterChanged (const juce::String& parameterID, float newValue) override;
    void changeListenerCallback (juce::ChangeBroadcaster* source) override;
    void authStateChanged (cloud::AuthManager&) override;
    void balanceChanged (cloud::AuthManager&, const cloud::CreditBalance& balance) override;
    void handleAsyncUpdate() override;
    void timerCallback() override;

    /** Called as soon as the JobClient holds a result (the `result` event, a cache load):
        stores it, installs the detected scale and root, and loads the selected stem if
        its file is already there. */
    void onResultAvailable (const cloud::JobResult& result);
    /** Loads the selected stem when an earlier attempt found its file still downloading. */
    void loadStemIfArrived();
    void applyScaleParametersToProcessor();

    /** Pushes every parameter into the engine atomics (constructor / state restore). */
    void syncEngineFromParameters();
    /** Drum pads are used only while the Drums category is selected with drum mode on. */
    void syncDrumModeToEngine();
    /** Any thread: asks the message thread for a debounced loadSelectedStem(). */
    void requestStemReload();
    /** Message thread: reloads `jobId` through the JobClient (cache first, then the server). */
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
    PluginSettings settings;
    cloud::AuthManager authManager;
    cloud::JobClient jobClient;
    engine::SamplerEngine engine;
    engine::ScaleLockProcessor scaleLock;
    juce::MidiKeyboardState keyboardState;
    juce::ChangeBroadcaster resultEvents;

    std::optional<cloud::JobResult> currentResult;
    juce::String lastJobId;
    /** Job whose analysis is already applied; a Downloading/Ready notification for the same
        job only checks whether the selected stem has landed. */
    juce::String analysisAppliedJobId;
    /** Job for which a stem is installed in the engine (isCurrentResultPlayable). */
    juce::String playableJobId;
    bool currentResultRestored = false;
    /** Set when reloadStem() found the stem still downloading; cleared once it loads. */
    bool stemLoadPending = false;
    bool pendingApplyAutoAdsr = true;
    bool demoLoadAttempted = false;
    juce::int64 dropTimeMs = 0;
    std::optional<juce::int64> dropToReadyMs;
    cloud::ApiClient::RequestId feedbackRequest = cloud::ApiClient::invalidRequest;

    std::atomic<bool> scaleParametersDirty { false };
    std::atomic<bool> stemReloadPending { false };
    std::atomic<std::uint32_t> noteOnBlocks { 0 };
    bool restoringCachedJob = false;
    int stemLoadSerial = 0;

    /** Guards lastJobId / pendingRestoreJobId, which state calls may touch off the message thread. */
    mutable juce::CriticalSection stateLock;
    juce::String pendingRestoreJobId;

    JUCE_DECLARE_WEAK_REFERENCEABLE (TonamorphAudioProcessor)
    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR (TonamorphAudioProcessor)
};

} // namespace tonamorph
