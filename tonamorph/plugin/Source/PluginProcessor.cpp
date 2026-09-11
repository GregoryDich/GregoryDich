#include "PluginProcessor.h"

#include "App/CrashReporter.h"
#include "App/DemoMorph.h"
#include "Core/FeedbackPayload.h"
#include "Core/ParameterText.h"
#include "Engine/AutoAdsr.h"
#include "PluginEditor.h"

#include <algorithm>
#include <array>
#include <utility>

namespace tonamorph
{

namespace
{
    constexpr std::array<const char*, 12> allParameterIds {
        ParamIds::attack, ParamIds::decay, ParamIds::sustain, ParamIds::release,
        ParamIds::cutoff, ParamIds::resonance, ParamIds::gain, ParamIds::category,
        ParamIds::rootTarget, ParamIds::drumMode, ParamIds::scaleMode, ParamIds::scaleRoot
    };

    /** The gain parameter's floor is silence, not a tiny signal. */
    constexpr float silenceDb = -60.0f;

    juce::NormalisableRange<float> skewedRange (float start, float end, float centre)
    {
        juce::NormalisableRange<float> range (start, end);
        range.setSkewForCentre (centre);
        return range;
    }

    //==============================================================================
    // Host-visible text for the parameters (and, through the slider attachments, the knob
    // text boxes): units in the text itself, so no separate label. Unreadable input falls
    // back to the parameter's default.

    using FloatFormat = std::string (*) (double);
    using FloatParse = std::optional<double> (*) (std::string_view);

    juce::AudioParameterFloatAttributes textAttributes (FloatFormat format, FloatParse parse, float defaultValue)
    {
        return juce::AudioParameterFloatAttributes()
            .withStringFromValueFunction ([format] (float value, int) { return juce::String (format (value)); })
            .withValueFromStringFunction ([parse, defaultValue] (const juce::String& text)
            {
                return static_cast<float> (parse (text.toStdString()).value_or (defaultValue));
            });
    }

    juce::AudioParameterFloatAttributes decibelAttributes (float defaultValue)
    {
        return juce::AudioParameterFloatAttributes()
            .withStringFromValueFunction ([] (float value, int) { return juce::String (core::formatDecibels (value, silenceDb)); })
            .withValueFromStringFunction ([defaultValue] (const juce::String& text)
            {
                return static_cast<float> (core::parseDecibels (text.toStdString(), silenceDb).value_or (defaultValue));
            });
    }

    juce::AudioParameterIntAttributes noteNameAttributes (int defaultValue)
    {
        return juce::AudioParameterIntAttributes()
            .withStringFromValueFunction ([] (int value, int) { return juce::String (core::formatNoteName (value)); })
            .withValueFromStringFunction ([defaultValue] (const juce::String& text)
            {
                return core::parseNoteName (text.toStdString()).value_or (defaultValue);
            });
    }

    juce::AudioParameterIntAttributes pitchClassAttributes (int defaultValue)
    {
        return juce::AudioParameterIntAttributes()
            .withStringFromValueFunction ([] (int value, int) { return juce::String (core::formatPitchClassName (value)); })
            .withValueFromStringFunction ([defaultValue] (const juce::String& text)
            {
                return core::parsePitchClassName (text.toStdString()).value_or (defaultValue);
            });
    }

    core::ScaleMode scaleModeFromIndex (int index)
    {
        return static_cast<core::ScaleMode> (juce::jlimit (0, core::numScaleModes - 1, index));
    }
} // namespace

//==============================================================================
TonamorphAudioProcessor::TonamorphAudioProcessor()
    : juce::AudioProcessor (BusesProperties().withOutput ("Output", juce::AudioChannelSet::stereo(), true)),
      apvts (*this, nullptr, stateTreeType, createParameterLayout()),
      apiClient(),
      settings(),
      authManager (apiClient, settings.getFile()),
      jobClient (apiClient, authManager)
{
    if (settings.isCrashReportingEnabled())
        CrashReporter::install (TONAMORPH_VERSION_STRING, apiClient.getConfig().hostName);

    attackParam     = apvts.getRawParameterValue (ParamIds::attack);
    decayParam      = apvts.getRawParameterValue (ParamIds::decay);
    sustainParam    = apvts.getRawParameterValue (ParamIds::sustain);
    releaseParam    = apvts.getRawParameterValue (ParamIds::release);
    cutoffParam     = apvts.getRawParameterValue (ParamIds::cutoff);
    resonanceParam  = apvts.getRawParameterValue (ParamIds::resonance);
    gainParam       = apvts.getRawParameterValue (ParamIds::gain);
    categoryParam   = apvts.getRawParameterValue (ParamIds::category);
    rootTargetParam = apvts.getRawParameterValue (ParamIds::rootTarget);
    drumModeParam   = apvts.getRawParameterValue (ParamIds::drumMode);
    scaleModeParam  = apvts.getRawParameterValue (ParamIds::scaleMode);
    scaleRootParam  = apvts.getRawParameterValue (ParamIds::scaleRoot);

    syncEngineFromParameters();
    applyScaleParametersToProcessor();

    for (const auto* id : allParameterIds)
        apvts.addParameterListener (id, this);

    jobClient.addChangeListener (this);
    authManager.addListener (this);
}

TonamorphAudioProcessor::~TonamorphAudioProcessor()
{
    cancelPendingUpdate();
    stopTimer();

    if (feedbackRequest != cloud::ApiClient::invalidRequest)
        apiClient.cancel (feedbackRequest);

    authManager.removeListener (this);
    jobClient.removeChangeListener (this);

    for (const auto* id : allParameterIds)
        apvts.removeParameterListener (id, this);
}

//==============================================================================
juce::AudioProcessorValueTreeState::ParameterLayout TonamorphAudioProcessor::createParameterLayout()
{
    juce::AudioProcessorValueTreeState::ParameterLayout layout;

    layout.add (std::make_unique<juce::AudioParameterFloat> (juce::ParameterID { ParamIds::attack, 1 }, "Attack",
                                                             skewedRange (1.0f, 2000.0f, 100.0f), 2.0f,
                                                             textAttributes (core::formatMilliseconds, core::parseMilliseconds, 2.0f)));
    layout.add (std::make_unique<juce::AudioParameterFloat> (juce::ParameterID { ParamIds::decay, 1 }, "Decay",
                                                             skewedRange (1.0f, 4000.0f, 300.0f), 120.0f,
                                                             textAttributes (core::formatMilliseconds, core::parseMilliseconds, 120.0f)));
    layout.add (std::make_unique<juce::AudioParameterFloat> (juce::ParameterID { ParamIds::sustain, 1 }, "Sustain",
                                                             juce::NormalisableRange<float> (0.0f, 1.0f), 0.8f,
                                                             textAttributes (core::formatPercent, core::parsePercent, 0.8f)));
    layout.add (std::make_unique<juce::AudioParameterFloat> (juce::ParameterID { ParamIds::release, 1 }, "Release",
                                                             skewedRange (5.0f, 5000.0f, 400.0f), 180.0f,
                                                             textAttributes (core::formatMilliseconds, core::parseMilliseconds, 180.0f)));
    layout.add (std::make_unique<juce::AudioParameterFloat> (juce::ParameterID { ParamIds::cutoff, 1 }, "Cutoff",
                                                             skewedRange (20.0f, 20000.0f, 1000.0f), 20000.0f,
                                                             textAttributes (core::formatHertz, core::parseHertz, 20000.0f)));
    layout.add (std::make_unique<juce::AudioParameterFloat> (juce::ParameterID { ParamIds::resonance, 1 }, "Resonance",
                                                             skewedRange (0.1f, 10.0f, 1.0f), 0.7071f,
                                                             textAttributes (core::formatRatio, core::parseRatio, 0.7071f)));
    layout.add (std::make_unique<juce::AudioParameterFloat> (juce::ParameterID { ParamIds::gain, 1 }, "Gain",
                                                             juce::NormalisableRange<float> (-60.0f, 12.0f), 0.0f,
                                                             decibelAttributes (0.0f)));
    layout.add (std::make_unique<juce::AudioParameterChoice> (juce::ParameterID { ParamIds::category, 1 }, "Category",
                                                              getCategoryLabels(), 0));
    layout.add (std::make_unique<juce::AudioParameterInt> (juce::ParameterID { ParamIds::rootTarget, 1 }, "Root Target",
                                                           24, 84, 48, noteNameAttributes (48)));
    layout.add (std::make_unique<juce::AudioParameterBool> (juce::ParameterID { ParamIds::drumMode, 1 }, "Drum Mode", false));
    layout.add (std::make_unique<juce::AudioParameterChoice> (juce::ParameterID { ParamIds::scaleMode, 1 }, "Scale Mode",
                                                              getScaleModeLabels(), 0));
    layout.add (std::make_unique<juce::AudioParameterInt> (juce::ParameterID { ParamIds::scaleRoot, 1 }, "Scale Root",
                                                           0, 11, 0, pitchClassAttributes (0)));
    return layout;
}

const juce::StringArray& TonamorphAudioProcessor::getCategoryLabels()
{
    static const juce::StringArray labels { "Bass", "Drums", "Synth", "Vocals" };
    return labels;
}

const juce::StringArray& TonamorphAudioProcessor::getScaleModeLabels()
{
    static const juce::StringArray labels { "Detected", "Major", "Minor", "PentatonicMajor", "PentatonicMinor", "Off" };
    return labels;
}

juce::String TonamorphAudioProcessor::stemNameForCategory (int categoryIndex)
{
    const auto index = static_cast<size_t> (juce::jlimit (0, numCategories - 1, categoryIndex));
    return cloud::stemNames[index];
}

//==============================================================================
void TonamorphAudioProcessor::prepareToPlay (double sampleRate, int samplesPerBlock)
{
    engine.prepare (sampleRate, samplesPerBlock);
    scaleLock.prepare();
    keyboardState.reset();
}

void TonamorphAudioProcessor::releaseResources()
{
    engine.releaseResources();
}

bool TonamorphAudioProcessor::isBusesLayoutSupported (const BusesLayout& layouts) const
{
    const auto& mainOut = layouts.getMainOutputChannelSet();
    return mainOut == juce::AudioChannelSet::stereo() || mainOut == juce::AudioChannelSet::mono();
}

void TonamorphAudioProcessor::processBlock (juce::AudioBuffer<float>& buffer, juce::MidiBuffer& midiMessages)
{
    juce::ScopedNoDenormals noDenormals;

    keyboardState.processNextMidiBuffer (midiMessages, 0, buffer.getNumSamples(), true);

    // First-sound hint: count blocks with a note-on. Raw bytes, no MidiMessage
    // construction, so nothing here can allocate.
    for (const auto metadata : midiMessages)
    {
        if (metadata.numBytes >= 3 && (metadata.data[0] & 0xf0) == 0x90 && metadata.data[2] > 0)
        {
            noteOnBlocks.fetch_add (1, std::memory_order_relaxed);
            break;
        }
    }

    scaleLock.process (midiMessages);
    engine.process (buffer, midiMessages);
}

juce::AudioProcessorEditor* TonamorphAudioProcessor::createEditor()
{
    return new TonamorphAudioProcessorEditor (*this);
}

double TonamorphAudioProcessor::getTailLengthSeconds() const
{
    return releaseParam != nullptr ? static_cast<double> (releaseParam->load()) / 1000.0 : 0.0;
}

//==============================================================================
void TonamorphAudioProcessor::getStateInformation (juce::MemoryBlock& destData)
{
    auto state = apvts.copyState();
    state.setProperty (lastJobIdProperty, getLastJobId(), nullptr);

    if (const auto xml = state.createXml())
        copyXmlToBinary (*xml, destData);
}

void TonamorphAudioProcessor::setStateInformation (const void* data, int sizeInBytes)
{
    const auto xml = getXmlFromBinary (data, sizeInBytes);

    if (xml == nullptr || ! xml->hasTagName (stateTreeType))
        return;

    const auto restored = juce::ValueTree::fromXml (*xml);
    const auto restoredJobId = restored.getProperty (lastJobIdProperty).toString().trim();

    apvts.replaceState (restored);

    {
        const juce::ScopedLock lock (stateLock);
        lastJobId = restoredJobId;
        pendingRestoreJobId = restoredJobId;
    }

    // replaceState() notified parameterChanged() for every changed parameter, so the engine
    // atomics are current; the message-thread reactions are delivered by the async update.
    scaleParametersDirty.store (true, std::memory_order_release);
    triggerAsyncUpdate();
}

//==============================================================================
juce::String TonamorphAudioProcessor::getLastJobId() const
{
    const juce::ScopedLock lock (stateLock);
    return lastJobId;
}

bool TonamorphAudioProcessor::isCurrentResultPlayable() const noexcept
{
    return currentResult.has_value() && playableJobId.isNotEmpty() && playableJobId == currentResult->jobId;
}

std::optional<cloud::KeyInfo> TonamorphAudioProcessor::getDetectedKey() const
{
    if (currentResult.has_value())
        return currentResult->analysis.key;

    return std::nullopt;
}

std::optional<double> TonamorphAudioProcessor::getDetectedBpm() const
{
    if (currentResult.has_value())
        return currentResult->analysis.bpm;

    return std::nullopt;
}

cloud::JobOptions TonamorphAudioProcessor::makeJobOptions() const
{
    cloud::JobOptions options;
    options.targetRootMidi = rootTargetParam != nullptr ? static_cast<int> (rootTargetParam->load()) : 48;
    options.drumSlices = true;
    options.idempotencyKey = juce::Uuid().toString();
    return options;
}

void TonamorphAudioProcessor::submitAudioFile (const juce::File& audioFile)
{
    dropTimeMs = juce::Time::currentTimeMillis();
    dropToReadyMs.reset();
    jobClient.submitFile (audioFile, makeJobOptions());
}

int TonamorphAudioProcessor::getSelectedCategory() const
{
    return categoryParam != nullptr ? static_cast<int> (categoryParam->load()) : 0;
}

bool TonamorphAudioProcessor::isDrumMode() const
{
    return drumModeParam != nullptr && drumModeParam->load() >= 0.5f;
}

void TonamorphAudioProcessor::loadSelectedStem()
{
    reloadStem (true);
}

//==============================================================================
void TonamorphAudioProcessor::loadDemoIfIdle()
{
    if (demoLoadAttempted || currentResult.has_value() || jobClient.getState() != cloud::JobClient::State::Idle)
        return;

    {
        const juce::ScopedLock lock (stateLock);

        if (pendingRestoreJobId.isNotEmpty() || lastJobId.isNotEmpty())
            return;
    }

    demoLoadAttempted = true;

    if (! DemoMorph::install (jobClient.getCacheRoot()))
        return;

    restoringCachedJob = false;
    jobClient.loadCachedJob (DemoMorph::jobId);
}

bool TonamorphAudioProcessor::canRateCurrentResult() const
{
    return currentResult.has_value() && ! currentResult->demo && currentResult->jobId.isNotEmpty()
        && ! settings.wasJobRated (currentResult->jobId);
}

void TonamorphAudioProcessor::submitFeedback (bool thumbsUp, const juce::String& reason, const juce::String& note,
                                              std::function<void (FeedbackOutcome)> onDone)
{
    if (! canRateCurrentResult() || feedbackRequest != cloud::ApiClient::invalidRequest)
    {
        if (onDone != nullptr)
            onDone (FeedbackOutcome::Failed);

        return;
    }

    const auto jobId = currentResult->jobId;
    const auto body = juce::String (core::buildFeedbackJson (thumbsUp, reason.toStdString(), note.toStdString(),
                                                             dropToReadyMs.has_value()
                                                                 ? std::optional<std::int64_t> (*dropToReadyMs)
                                                                 : std::nullopt));

    feedbackRequest = apiClient.submitFeedback (jobId, body,
        [weakThis = juce::WeakReference<TonamorphAudioProcessor> (this), jobId, onDone]
        (cloud::ApiClient::Response<cloud::FeedbackResponse> response)
        {
            if (weakThis == nullptr)
                return;

            weakThis->feedbackRequest = cloud::ApiClient::invalidRequest;
            auto outcome = FeedbackOutcome::Failed;

            if (response.ok())
            {
                weakThis->settings.markJobRated (jobId);
                outcome = response.value->refunded ? FeedbackOutcome::Refunded : FeedbackOutcome::Sent;

                if (response.value->refunded)
                {
                    if (response.value->balance.has_value())
                        weakThis->authManager.updateBalance (*response.value->balance);

                    weakThis->authManager.refreshBalance();
                }
            }
            else if (response.statusCode == 404)
            {
                // The route is not deployed yet: the rating cannot land anywhere, so do not
                // keep asking for it.
                weakThis->settings.markJobRated (jobId);
                outcome = FeedbackOutcome::Sent;
            }

            weakThis->resultEvents.sendChangeMessage();

            if (onDone != nullptr)
                onDone (outcome);
        });
}

void TonamorphAudioProcessor::setCrashReportingEnabled (bool enabled)
{
    settings.setCrashReportingEnabled (enabled);

    if (enabled)
        CrashReporter::install (TONAMORPH_VERSION_STRING, apiClient.getConfig().hostName);
}

void TonamorphAudioProcessor::flushCrashReports()
{
    static bool flushedThisProcess = false;

    if (std::exchange (flushedThisProcess, true))
        return;

    CrashReporter::flushPendingReports (apiClient, settings.isCrashReportingEnabled());
}

//==============================================================================
void TonamorphAudioProcessor::parameterChanged (const juce::String& parameterID, float newValue)
{
    auto& voice = engine.getVoiceParameters();

    if (parameterID == ParamIds::attack)
    {
        voice.attackMs.store (newValue, std::memory_order_relaxed);
    }
    else if (parameterID == ParamIds::decay)
    {
        voice.decayMs.store (newValue, std::memory_order_relaxed);
    }
    else if (parameterID == ParamIds::sustain)
    {
        voice.sustain.store (newValue, std::memory_order_relaxed);
    }
    else if (parameterID == ParamIds::release)
    {
        voice.releaseMs.store (newValue, std::memory_order_relaxed);
    }
    else if (parameterID == ParamIds::cutoff)
    {
        engine.setFilter (newValue, resonanceParam->load());
    }
    else if (parameterID == ParamIds::resonance)
    {
        engine.setFilter (cutoffParam->load(), newValue);
    }
    else if (parameterID == ParamIds::gain)
    {
        engine.setGain (juce::Decibels::decibelsToGain (newValue, silenceDb));
    }
    else if (parameterID == ParamIds::drumMode)
    {
        syncDrumModeToEngine();

        if (getSelectedCategory() == static_cast<int> (Category::Drums))
            requestStemReload();
    }
    else if (parameterID == ParamIds::category)
    {
        syncDrumModeToEngine();
        requestStemReload();
    }
    else if (parameterID == ParamIds::rootTarget)
    {
        requestStemReload();
    }
    else if (parameterID == ParamIds::scaleMode || parameterID == ParamIds::scaleRoot)
    {
        scaleParametersDirty.store (true, std::memory_order_release);
        triggerAsyncUpdate();
    }
}

void TonamorphAudioProcessor::changeListenerCallback (juce::ChangeBroadcaster* source)
{
    if (source != &jobClient)
        return;

    using State = cloud::JobClient::State;

    switch (jobClient.getState())
    {
        // The `result` event puts the JobClient into Downloading with the result already
        // parsed: that is when the analysis goes live. Each later notification is a stem
        // landing, and Ready is the last of them.
        case State::Downloading:
        case State::Ready:
            if (const auto& result = jobClient.getResult(); result.has_value())
            {
                if (result->jobId != analysisAppliedJobId)
                    onResultAvailable (*result);
                else
                    loadStemIfArrived();
            }
            break;

        case State::Failed:
        case State::Cancelled:
            restoringCachedJob = false;
            stemLoadPending = false;
            break;

        case State::Idle:
        case State::Encoding:
        case State::Submitting:
        case State::Queued:
        case State::Running:
            break;
    }
}

void TonamorphAudioProcessor::authStateChanged (cloud::AuthManager& auth)
{
    // A session that ended mid-job can no longer stream or download: stop following it.
    if (! auth.isLoggedIn() && auth.getState() != cloud::AuthManager::State::LoggingIn && jobClient.isRunning())
        jobClient.cancel();
}

void TonamorphAudioProcessor::balanceChanged (cloud::AuthManager&, const cloud::CreditBalance& balance)
{
    juce::ignoreUnused (balance);
}

void TonamorphAudioProcessor::handleAsyncUpdate()
{
    if (scaleParametersDirty.exchange (false, std::memory_order_acq_rel))
        applyScaleParametersToProcessor();

    juce::String jobIdToRestore;
    {
        const juce::ScopedLock lock (stateLock);
        jobIdToRestore.swapWith (pendingRestoreJobId);
    }

    if (jobIdToRestore.isNotEmpty())
        restoreCachedJob (jobIdToRestore);

    if (stemReloadPending.exchange (false, std::memory_order_acq_rel))
        startTimer (stemReloadDebounceMs);
}

void TonamorphAudioProcessor::timerCallback()
{
    stopTimer();
    loadSelectedStem();
}

//==============================================================================
void TonamorphAudioProcessor::onResultAvailable (const cloud::JobResult& result)
{
    // A job restored from the host's saved state keeps the saved root and envelope; a
    // freshly processed job takes the analysis defaults.
    const bool restored = std::exchange (restoringCachedJob, false) && result.jobId == getLastJobId();

    currentResult = result;
    currentResultRestored = restored;
    analysisAppliedJobId = result.jobId;
    playableJobId.clear();
    stemLoadPending = false;

    if (restored || result.demo)
        dropToReadyMs.reset();

    if (! result.demo)
    {
        const juce::ScopedLock lock (stateLock);
        lastJobId = result.jobId;
    }

    scaleLock.setDetectedScale (result.analysis.key.scalePitchClasses);

    if (! restored)
        setScaleRootParameter (core::toPitchClass (result.analysis.key.rootMidi));

    applyScaleParametersToProcessor();
    reloadStem (! restored);
    resultEvents.sendChangeMessage();
}

void TonamorphAudioProcessor::loadStemIfArrived()
{
    if (stemLoadPending && currentResult.has_value())
        reloadStem (pendingApplyAutoAdsr);
}

void TonamorphAudioProcessor::applyScaleParametersToProcessor()
{
    const int modeIndex = scaleModeParam != nullptr ? static_cast<int> (scaleModeParam->load()) : 0;
    const int root = scaleRootParam != nullptr ? static_cast<int> (scaleRootParam->load()) : 0;
    scaleLock.setMode (scaleModeFromIndex (modeIndex), root);
}

void TonamorphAudioProcessor::syncEngineFromParameters()
{
    engine.setAdsr ({ attackParam->load(), decayParam->load(), sustainParam->load(), releaseParam->load() });
    engine.setFilter (cutoffParam->load(), resonanceParam->load());
    engine.setGain (juce::Decibels::decibelsToGain (gainParam->load(), silenceDb));
    syncDrumModeToEngine();
}

void TonamorphAudioProcessor::syncDrumModeToEngine()
{
    engine.setDrumMode (isDrumMode() && getSelectedCategory() == static_cast<int> (Category::Drums));
}

void TonamorphAudioProcessor::requestStemReload()
{
    stemReloadPending.store (true, std::memory_order_release);
    triggerAsyncUpdate();
}

void TonamorphAudioProcessor::restoreCachedJob (const juce::String& jobIdToRestore)
{
    if (currentResult.has_value() && currentResult->jobId == jobIdToRestore)
        return;

    if (jobClient.isRunning())
        return;

    // Cache first, then the server while signed in; otherwise the JobClient reports
    // `cache_missing` and the UI says so.
    restoringCachedJob = true;
    jobClient.loadCachedJob (jobIdToRestore);
}

void TonamorphAudioProcessor::setScaleRootParameter (int pitchClass)
{
    if (auto* parameter = apvts.getParameter (ParamIds::scaleRoot))
    {
        parameter->beginChangeGesture();
        parameter->setValueNotifyingHost (parameter->convertTo0to1 (static_cast<float> (pitchClass)));
        parameter->endChangeGesture();
    }
}

void TonamorphAudioProcessor::applyAdsr (const core::Adsr& adsr)
{
    auto* attack  = apvts.getParameter (ParamIds::attack);
    auto* decay   = apvts.getParameter (ParamIds::decay);
    auto* sustain = apvts.getParameter (ParamIds::sustain);
    auto* release = apvts.getParameter (ParamIds::release);

    if (attack != nullptr && decay != nullptr && sustain != nullptr && release != nullptr)
        engine::applyAdsrToParameters (*attack, *decay, *sustain, *release, adsr);
}

void TonamorphAudioProcessor::reloadStem (bool applyAutoAdsr)
{
    if (! currentResult.has_value())
        return;

    const auto stemName = stemNameForCategory (getSelectedCategory());
    const auto* info = currentResult->findStem (stemName);

    if (info == nullptr)
        return;

    const auto wavFile = cloud::JobClient::jobDirectoryFor (jobClient.getCacheRoot(), currentResult->jobId)
                             .getChildFile (stemName + ".wav");

    if (! wavFile.existsAsFile())
    {
        // Still downloading: loadStemIfArrived() retries on the next JobClient notification.
        stemLoadPending = true;
        pendingApplyAutoAdsr = applyAutoAdsr;
        return;
    }

    stemLoadPending = false;

    const bool wantsDrumKit = isDrumMode() && getSelectedCategory() == static_cast<int> (Category::Drums);

    if (applyAutoAdsr && info->suggestedAdsr.has_value())
        applyAdsr (*info->suggestedAdsr);

    // Without a server suggestion the envelope is derived while the sound is built, so it
    // can only be applied once the load has finished (drum kits carry no envelope).
    const bool applyDerivedAdsr = applyAutoAdsr && ! info->suggestedAdsr.has_value() && ! wantsDrumKit;
    const int serial = ++stemLoadSerial;
    const auto jobId = currentResult->jobId;

    auto onLoaded = [weakThis = juce::WeakReference<TonamorphAudioProcessor> (this), serial, applyDerivedAdsr, jobId]
                    (bool ok, const juce::String&)
    {
        if (weakThis == nullptr || ! ok || serial != weakThis->stemLoadSerial)
            return;

        if (applyDerivedAdsr)
            if (const auto stem = weakThis->engine.getCurrentStem())
                weakThis->applyAdsr (stem->getAdsr());

        auto& self = *weakThis;

        if (self.currentResult.has_value() && self.currentResult->jobId == jobId)
        {
            const bool firstStemOfJob = self.playableJobId != jobId;
            self.playableJobId = jobId;

            if (firstStemOfJob && ! self.currentResultRestored && ! self.currentResult->demo && self.dropTimeMs > 0)
                self.dropToReadyMs = std::max<juce::int64> (0, juce::Time::currentTimeMillis() - self.dropTimeMs);

            self.resultEvents.sendChangeMessage();
        }
    };

    if (wantsDrumKit)
    {
        engine.loadDrumKit (wavFile, *info, std::move (onLoaded));
        return;
    }

    engine::StemSound::BuildOptions options;
    options.targetRootMidi = rootTargetParam != nullptr ? static_cast<int> (rootTargetParam->load()) : 48;
    engine.loadStem (wavFile, *info, options, std::move (onLoaded));
}

} // namespace tonamorph

//==============================================================================
juce::AudioProcessor* JUCE_CALLTYPE createPluginFilter()
{
    return new tonamorph::TonamorphAudioProcessor();
}
