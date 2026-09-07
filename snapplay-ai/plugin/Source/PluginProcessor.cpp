#include "PluginProcessor.h"

#include "Engine/AutoAdsr.h"
#include "PluginEditor.h"

namespace snapplay
{

namespace
{
    juce::NormalisableRange<float> skewedRange (float start, float end, float centre)
    {
        juce::NormalisableRange<float> range (start, end);
        range.setSkewForCentre (centre);
        return range;
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

    for (const auto* id : { ParamIds::attack, ParamIds::decay, ParamIds::sustain, ParamIds::release,
                            ParamIds::cutoff, ParamIds::resonance, ParamIds::gain, ParamIds::category,
                            ParamIds::rootTarget, ParamIds::drumMode, ParamIds::scaleMode, ParamIds::scaleRoot })
        apvts.addParameterListener (id, this);

    jobClient.addChangeListener (this);
    authManager.addListener (this);
}

SnapPlayAudioProcessor::~SnapPlayAudioProcessor()
{
    authManager.removeListener (this);
    jobClient.removeChangeListener (this);
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
    juce::ignoreUnused (destData);
}

void SnapPlayAudioProcessor::setStateInformation (const void* data, int sizeInBytes)
{
    juce::ignoreUnused (data, sizeInBytes);
}

//==============================================================================
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
}

//==============================================================================
void SnapPlayAudioProcessor::parameterChanged (const juce::String& parameterID, float newValue)
{
    juce::ignoreUnused (parameterID, newValue);
}

void SnapPlayAudioProcessor::changeListenerCallback (juce::ChangeBroadcaster* source)
{
    juce::ignoreUnused (source);
}

void SnapPlayAudioProcessor::authStateChanged (cloud::AuthManager&)
{
}

void SnapPlayAudioProcessor::balanceChanged (cloud::AuthManager&, const cloud::CreditBalance& balance)
{
    juce::ignoreUnused (balance);
}

void SnapPlayAudioProcessor::onJobReady (const cloud::JobResult& result)
{
    juce::ignoreUnused (result);
}

void SnapPlayAudioProcessor::applyScaleParametersToProcessor()
{
}

} // namespace snapplay

//==============================================================================
juce::AudioProcessor* JUCE_CALLTYPE createPluginFilter()
{
    return new snapplay::SnapPlayAudioProcessor();
}
