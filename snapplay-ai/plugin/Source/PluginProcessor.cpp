#include "PluginProcessor.h"

#include "Engine/AutoAdsr.h"
#include "PluginEditor.h"

#include <array>
#include <utility>

namespace snapplay
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

    core::ScaleMode scaleModeFromIndex (int index)
    {
        return static_cast<core::ScaleMode> (juce::jlimit (0, core::numScaleModes - 1, index));
    }
} // namespace

//==============================================================================
SnapPlayAudioProcessor::SnapPlayAudioProcessor()
    : juce::AudioProcessor (BusesProperties().withOutput ("Output", juce::AudioChannelSet::stereo(), true)),
      apvts (*this, nullptr, stateTreeType, createParameterLayout()),
      apiClient(),
      authManager (apiClient),
      jobClient (apiClient, authManager)
{
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

SnapPlayAudioProcessor::~SnapPlayAudioProcessor()
{
    cancelPendingUpdate();
    stopTimer();

    authManager.removeListener (this);
    jobClient.removeChangeListener (this);

    for (const auto* id : allParameterIds)
        apvts.removeParameterListener (id, this);
}

//==============================================================================
juce::AudioProcessorValueTreeState::ParameterLayout SnapPlayAudioProcessor::createParameterLayout()
{
    juce::AudioProcessorValueTreeState::ParameterLayout layout;

    layout.add (std::make_unique<juce::AudioParameterFloat> (juce::ParameterID { ParamIds::attack, 1 }, "Attack",
                                                             skewedRange (1.0f, 2000.0f, 100.0f), 2.0f,
                                                             juce::AudioParameterFloatAttributes().withLabel ("ms")));
    layout.add (std::make_unique<juce::AudioParameterFloat> (juce::ParameterID { ParamIds::decay, 1 }, "Decay",
                                                             skewedRange (1.0f, 4000.0f, 300.0f), 120.0f,
                                                             juce::AudioParameterFloatAttributes().withLabel ("ms")));
    layout.add (std::make_unique<juce::AudioParameterFloat> (juce::ParameterID { ParamIds::sustain, 1 }, "Sustain",
                                                             juce::NormalisableRange<float> (0.0f, 1.0f), 0.8f));
    layout.add (std::make_unique<juce::AudioParameterFloat> (juce::ParameterID { ParamIds::release, 1 }, "Release",
                                                             skewedRange (5.0f, 5000.0f, 400.0f), 180.0f,
                                                             juce::AudioParameterFloatAttributes().withLabel ("ms")));
    layout.add (std::make_unique<juce::AudioParameterFloat> (juce::ParameterID { ParamIds::cutoff, 1 }, "Cutoff",
                                                             skewedRange (20.0f, 20000.0f, 1000.0f), 20000.0f,
                                                             juce::AudioParameterFloatAttributes().withLabel ("Hz")));
    layout.add (std::make_unique<juce::AudioParameterFloat> (juce::ParameterID { ParamIds::resonance, 1 }, "Resonance",
                                                             skewedRange (0.1f, 10.0f, 1.0f), 0.7071f));
    layout.add (std::make_unique<juce::AudioParameterFloat> (juce::ParameterID { ParamIds::gain, 1 }, "Gain",
                                                             juce::NormalisableRange<float> (-60.0f, 12.0f), 0.0f,
                                                             juce::AudioParameterFloatAttributes().withLabel ("dB")));
    layout.add (std::make_unique<juce::AudioParameterChoice> (juce::ParameterID { ParamIds::category, 1 }, "Category",
                                                              getCategoryLabels(), 0));
    layout.add (std::make_unique<juce::AudioParameterInt> (juce::ParameterID { ParamIds::rootTarget, 1 }, "Root Target",
                                                           24, 84, 48));
    layout.add (std::make_unique<juce::AudioParameterBool> (juce::ParameterID { ParamIds::drumMode, 1 }, "Drum Mode", false));
    layout.add (std::make_unique<juce::AudioParameterChoice> (juce::ParameterID { ParamIds::scaleMode, 1 }, "Scale Mode",
                                                              getScaleModeLabels(), 0));
    layout.add (std::make_unique<juce::AudioParameterInt> (juce::ParameterID { ParamIds::scaleRoot, 1 }, "Scale Root",
                                                           0, 11, 0));
    return layout;
}

const juce::StringArray& SnapPlayAudioProcessor::getCategoryLabels()
{
    static const juce::StringArray labels { "Bass", "Drums", "Synth", "Vocals" };
    return labels;
}

const juce::StringArray& SnapPlayAudioProcessor::getScaleModeLabels()
{
    static const juce::StringArray labels { "Detected", "Major", "Minor", "PentatonicMajor", "PentatonicMinor", "Off" };
    return labels;
}

juce::String SnapPlayAudioProcessor::stemNameForCategory (int categoryIndex)
{
    const auto index = static_cast<size_t> (juce::jlimit (0, numCategories - 1, categoryIndex));
    return cloud::stemNames[index];
}

//==============================================================================
void SnapPlayAudioProcessor::prepareToPlay (double sampleRate, int samplesPerBlock)
{
    engine.prepare (sampleRate, samplesPerBlock);
    scaleLock.prepare();
    keyboardState.reset();
}

void SnapPlayAudioProcessor::releaseResources()
{
    engine.releaseResources();
}

bool SnapPlayAudioProcessor::isBusesLayoutSupported (const BusesLayout& layouts) const
{
    const auto& mainOut = layouts.getMainOutputChannelSet();
    return mainOut == juce::AudioChannelSet::stereo() || mainOut == juce::AudioChannelSet::mono();
}

void SnapPlayAudioProcessor::processBlock (juce::AudioBuffer<float>& buffer, juce::MidiBuffer& midiMessages)
{
    juce::ScopedNoDenormals noDenormals;

    keyboardState.processNextMidiBuffer (midiMessages, 0, buffer.getNumSamples(), true);
    scaleLock.process (midiMessages);
    engine.process (buffer, midiMessages);
}

juce::AudioProcessorEditor* SnapPlayAudioProcessor::createEditor()
{
    return new SnapPlayAudioProcessorEditor (*this);
}

double SnapPlayAudioProcessor::getTailLengthSeconds() const
{
    return releaseParam != nullptr ? static_cast<double> (releaseParam->load()) / 1000.0 : 0.0;
}

//==============================================================================
void SnapPlayAudioProcessor::getStateInformation (juce::MemoryBlock& destData)
{
    auto state = apvts.copyState();
    state.setProperty (lastJobIdProperty, getLastJobId(), nullptr);

    if (const auto xml = state.createXml())
        copyXmlToBinary (*xml, destData);
}

void SnapPlayAudioProcessor::setStateInformation (const void* data, int sizeInBytes)
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
juce::String SnapPlayAudioProcessor::getLastJobId() const
{
    const juce::ScopedLock lock (stateLock);
    return lastJobId;
}

std::optional<cloud::KeyInfo> SnapPlayAudioProcessor::getDetectedKey() const
{
    if (currentResult.has_value())
        return currentResult->analysis.key;

    return std::nullopt;
}

std::optional<double> SnapPlayAudioProcessor::getDetectedBpm() const
{
    if (currentResult.has_value())
        return currentResult->analysis.bpm;

    return std::nullopt;
}

cloud::JobOptions SnapPlayAudioProcessor::makeJobOptions() const
{
    cloud::JobOptions options;
    options.targetRootMidi = rootTargetParam != nullptr ? static_cast<int> (rootTargetParam->load()) : 48;
    options.drumSlices = true;
    options.idempotencyKey = juce::Uuid().toString();
    return options;
}

void SnapPlayAudioProcessor::submitAudioFile (const juce::File& audioFile)
{
    jobClient.submitFile (audioFile, makeJobOptions());
}

int SnapPlayAudioProcessor::getSelectedCategory() const
{
    return categoryParam != nullptr ? static_cast<int> (categoryParam->load()) : 0;
}

bool SnapPlayAudioProcessor::isDrumMode() const
{
    return drumModeParam != nullptr && drumModeParam->load() >= 0.5f;
}

void SnapPlayAudioProcessor::loadSelectedStem()
{
    reloadStem (true);
}

//==============================================================================
void SnapPlayAudioProcessor::parameterChanged (const juce::String& parameterID, float newValue)
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

void SnapPlayAudioProcessor::changeListenerCallback (juce::ChangeBroadcaster* source)
{
    if (source != &jobClient)
        return;

    using State = cloud::JobClient::State;

    switch (jobClient.getState())
    {
        case State::Ready:
            if (const auto& result = jobClient.getResult(); result.has_value())
                onJobReady (*result);
            break;

        case State::Failed:
        case State::Cancelled:
            restoringCachedJob = false;
            break;

        case State::Idle:
        case State::Encoding:
        case State::Submitting:
        case State::Queued:
        case State::Running:
        case State::Downloading:
            break;
    }
}

void SnapPlayAudioProcessor::authStateChanged (cloud::AuthManager& auth)
{
    // A session that ended mid-job can no longer stream or download: stop following it.
    if (! auth.isLoggedIn() && auth.getState() != cloud::AuthManager::State::LoggingIn && jobClient.isRunning())
        jobClient.cancel();
}

void SnapPlayAudioProcessor::balanceChanged (cloud::AuthManager&, const cloud::CreditBalance& balance)
{
    juce::ignoreUnused (balance);
}

void SnapPlayAudioProcessor::handleAsyncUpdate()
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

void SnapPlayAudioProcessor::timerCallback()
{
    stopTimer();
    loadSelectedStem();
}

//==============================================================================
void SnapPlayAudioProcessor::onJobReady (const cloud::JobResult& result)
{
    // A job restored from the host's saved state keeps the saved root and envelope; a
    // freshly processed job takes the analysis defaults.
    const bool restored = std::exchange (restoringCachedJob, false) && result.jobId == getLastJobId();

    currentResult = result;

    {
        const juce::ScopedLock lock (stateLock);
        lastJobId = result.jobId;
    }

    scaleLock.setDetectedScale (result.analysis.key.scalePitchClasses);

    if (! restored)
        setScaleRootParameter (core::toPitchClass (result.analysis.key.rootMidi));

    applyScaleParametersToProcessor();
    reloadStem (! restored);
}

void SnapPlayAudioProcessor::applyScaleParametersToProcessor()
{
    const int modeIndex = scaleModeParam != nullptr ? static_cast<int> (scaleModeParam->load()) : 0;
    const int root = scaleRootParam != nullptr ? static_cast<int> (scaleRootParam->load()) : 0;
    scaleLock.setMode (scaleModeFromIndex (modeIndex), root);
}

void SnapPlayAudioProcessor::syncEngineFromParameters()
{
    engine.setAdsr ({ attackParam->load(), decayParam->load(), sustainParam->load(), releaseParam->load() });
    engine.setFilter (cutoffParam->load(), resonanceParam->load());
    engine.setGain (juce::Decibels::decibelsToGain (gainParam->load(), silenceDb));
    syncDrumModeToEngine();
}

void SnapPlayAudioProcessor::syncDrumModeToEngine()
{
    engine.setDrumMode (isDrumMode() && getSelectedCategory() == static_cast<int> (Category::Drums));
}

void SnapPlayAudioProcessor::requestStemReload()
{
    stemReloadPending.store (true, std::memory_order_release);
    triggerAsyncUpdate();
}

void SnapPlayAudioProcessor::restoreCachedJob (const juce::String& jobIdToRestore)
{
    if (currentResult.has_value() && currentResult->jobId == jobIdToRestore)
        return;

    if (jobClient.isRunning())
        return;

    if (! cloud::JobClient::jobDirectoryFor (jobClient.getCacheRoot(), jobIdToRestore).isDirectory())
        return;

    restoringCachedJob = true;
    jobClient.loadCachedJob (jobIdToRestore);
}

void SnapPlayAudioProcessor::setScaleRootParameter (int pitchClass)
{
    if (auto* parameter = apvts.getParameter (ParamIds::scaleRoot))
    {
        parameter->beginChangeGesture();
        parameter->setValueNotifyingHost (parameter->convertTo0to1 (static_cast<float> (pitchClass)));
        parameter->endChangeGesture();
    }
}

void SnapPlayAudioProcessor::applyAdsr (const core::Adsr& adsr)
{
    auto* attack  = apvts.getParameter (ParamIds::attack);
    auto* decay   = apvts.getParameter (ParamIds::decay);
    auto* sustain = apvts.getParameter (ParamIds::sustain);
    auto* release = apvts.getParameter (ParamIds::release);

    if (attack != nullptr && decay != nullptr && sustain != nullptr && release != nullptr)
        engine::applyAdsrToParameters (*attack, *decay, *sustain, *release, adsr);
}

void SnapPlayAudioProcessor::reloadStem (bool applyAutoAdsr)
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
        return;

    const bool wantsDrumKit = isDrumMode() && getSelectedCategory() == static_cast<int> (Category::Drums);

    if (applyAutoAdsr && info->suggestedAdsr.has_value())
        applyAdsr (*info->suggestedAdsr);

    // Without a server suggestion the envelope is derived while the sound is built, so it
    // can only be applied once the load has finished (drum kits carry no envelope).
    const bool applyDerivedAdsr = applyAutoAdsr && ! info->suggestedAdsr.has_value() && ! wantsDrumKit;
    const int serial = ++stemLoadSerial;

    auto onLoaded = [weakThis = juce::WeakReference<SnapPlayAudioProcessor> (this), serial, applyDerivedAdsr]
                    (bool ok, const juce::String&)
    {
        if (weakThis == nullptr || ! ok || serial != weakThis->stemLoadSerial)
            return;

        if (applyDerivedAdsr)
            if (const auto stem = weakThis->engine.getCurrentStem())
                weakThis->applyAdsr (stem->getAdsr());
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

} // namespace snapplay

//==============================================================================
juce::AudioProcessor* JUCE_CALLTYPE createPluginFilter()
{
    return new snapplay::SnapPlayAudioProcessor();
}
