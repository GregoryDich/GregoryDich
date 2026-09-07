#include "Cloud/UploadEncoder.h"

#include <cmath>
#include <memory>

namespace snapplay::cloud
{

namespace
{

constexpr int flacBitDepth = 16;
constexpr int flacQuality = 5;
/** Never shorten below one second when squeezing under the byte cap. */
constexpr int minEncodedSamples = 44100;

juce::AudioFormatManager& getFormatManager()
{
    static const auto manager = []
    {
        auto created = std::make_unique<juce::AudioFormatManager>();
        created->registerBasicFormats();
        return created;
    }();

    return *manager;
}

/** Folds any channel count down to at most two: mono and stereo pass through, wider
    layouts are averaged round-robin onto left/right so the level never rises. */
juce::AudioBuffer<float> mixDown (const juce::AudioBuffer<float>& source, int numSamples)
{
    const int sourceChannels = source.getNumChannels();
    const int outChannels = juce::jmin (sourceChannels, UploadEncoder::maxChannels);
    juce::AudioBuffer<float> out (outChannels, numSamples);
    out.clear();

    if (sourceChannels <= UploadEncoder::maxChannels)
    {
        for (int ch = 0; ch < outChannels; ++ch)
            out.copyFrom (ch, 0, source, ch, 0, numSamples);

        return out;
    }

    int contributions[UploadEncoder::maxChannels] = {};

    for (int ch = 0; ch < sourceChannels; ++ch)
        ++contributions[ch % outChannels];

    for (int ch = 0; ch < sourceChannels; ++ch)
    {
        const int target = ch % outChannels;
        out.addFrom (target, 0, source, ch, 0, numSamples, 1.0f / static_cast<float> (contributions[target]));
    }

    return out;
}

juce::AudioBuffer<float> resample (const juce::AudioBuffer<float>& source, double sourceRate, double targetRate)
{
    const int numIn = source.getNumSamples();

    if (juce::approximatelyEqual (sourceRate, targetRate))
        return source;

    const double ratio = sourceRate / targetRate;
    const int numOut = juce::jmax (0, static_cast<int> (std::floor (static_cast<double> (numIn) / ratio)));
    juce::AudioBuffer<float> out (source.getNumChannels(), numOut);

    for (int ch = 0; ch < source.getNumChannels(); ++ch)
    {
        juce::LagrangeInterpolator interpolator;
        interpolator.reset();
        interpolator.process (ratio, source.getReadPointer (ch), out.getWritePointer (ch), numOut, numIn, 0);
    }

    return out;
}

bool encodeFlac (const juce::AudioBuffer<float>& audio, int numSamples, juce::MemoryBlock& out)
{
    out.reset();
    juce::FlacAudioFormat flac;

    // The writer takes ownership of the stream in every path createWriterFor() can take
    // with a valid bit depth, so it must not be held by a smart pointer here.
    auto* stream = new juce::MemoryOutputStream (out, false);
    std::unique_ptr<juce::AudioFormatWriter> writer (flac.createWriterFor (stream, UploadEncoder::targetSampleRate,
                                                                            static_cast<unsigned int> (audio.getNumChannels()),
                                                                            flacBitDepth, {}, flacQuality));

    if (writer == nullptr)
        return false;

    const bool ok = writer->writeFromAudioSampleBuffer (audio, 0, numSamples);
    writer.reset();   // flushes the encoder and finalises `out`
    return ok && out.getSize() > 0;
}

/** Resamples, encodes and — if the FLAC still exceeds the byte cap — re-encodes
    progressively shorter clips until it fits. `audio` has at most two channels. */
UploadEncoder::Result encodeSamples (const juce::AudioBuffer<float>& audio, double sourceRate,
                                     double inputDurationSeconds, bool truncated)
{
    UploadEncoder::Result result;
    result.inputDurationSeconds = inputDurationSeconds;
    result.truncated = truncated;

    if (audio.getNumChannels() == 0 || audio.getNumSamples() == 0)
    {
        result.errorMessage = "The audio contains no samples";
        return result;
    }

    const auto resampled = resample (audio, sourceRate, UploadEncoder::targetSampleRate);
    int numSamples = resampled.getNumSamples();

    if (numSamples == 0)
    {
        result.errorMessage = "The audio is too short to encode";
        return result;
    }

    result.sampleRate = static_cast<int> (UploadEncoder::targetSampleRate);
    result.numChannels = resampled.getNumChannels();

    for (;;)
    {
        juce::MemoryBlock encoded;

        if (! encodeFlac (resampled, numSamples, encoded))
        {
            result.errorMessage = "FLAC encoding failed";
            return result;
        }

        if (encoded.getSize() <= UploadEncoder::maxBytes || numSamples <= minEncodedSamples)
        {
            result.flacData = std::move (encoded);
            break;
        }

        const double shrink = static_cast<double> (UploadEncoder::maxBytes) / static_cast<double> (encoded.getSize()) * 0.95;
        numSamples = juce::jmax (minEncodedSamples, static_cast<int> (static_cast<double> (numSamples) * shrink));
        result.truncated = true;
    }

    result.encodedDurationSeconds = static_cast<double> (numSamples) / UploadEncoder::targetSampleRate;
    return result;
}

} // namespace

//==============================================================================
UploadEncoder::Result UploadEncoder::encodeFile (const juce::File& file)
{
    std::unique_ptr<juce::AudioFormatReader> reader (getFormatManager().createReaderFor (file));

    if (reader == nullptr)
    {
        Result result;
        result.errorMessage = "Unsupported or unreadable audio file: " + file.getFileName();
        return result;
    }

    if (reader->sampleRate <= 0.0 || reader->numChannels == 0 || reader->lengthInSamples <= 0)
    {
        Result result;
        result.errorMessage = "The audio file contains no audio: " + file.getFileName();
        return result;
    }

    const double sourceRate = reader->sampleRate;
    const auto maxSamples = static_cast<juce::int64> (std::llround (maxSeconds * sourceRate));
    const auto samplesToRead = juce::jmin (reader->lengthInSamples, maxSamples);
    const bool truncated = reader->lengthInSamples > maxSamples;

    juce::AudioBuffer<float> raw (static_cast<int> (reader->numChannels), static_cast<int> (samplesToRead));

    if (! reader->read (raw.getArrayOfWritePointers(), raw.getNumChannels(), 0, static_cast<int> (samplesToRead)))
    {
        Result result;
        result.errorMessage = "Could not decode the audio file: " + file.getFileName();
        return result;
    }

    const double inputDuration = static_cast<double> (reader->lengthInSamples) / sourceRate;
    reader.reset();

    return encodeSamples (mixDown (raw, raw.getNumSamples()), sourceRate, inputDuration, truncated);
}

UploadEncoder::Result UploadEncoder::encodeBuffer (const juce::AudioBuffer<float>& audio, double sourceSampleRate)
{
    if (sourceSampleRate <= 0.0)
    {
        Result result;
        result.errorMessage = "Invalid sample rate";
        return result;
    }

    const auto maxSamples = static_cast<juce::int64> (std::llround (maxSeconds * sourceSampleRate));
    const int numSamples = static_cast<int> (juce::jmin (static_cast<juce::int64> (audio.getNumSamples()), maxSamples));
    const bool truncated = audio.getNumSamples() > maxSamples;
    const double inputDuration = static_cast<double> (audio.getNumSamples()) / sourceSampleRate;

    return encodeSamples (mixDown (audio, numSamples), sourceSampleRate, inputDuration, truncated);
}

bool UploadEncoder::isSupportedFile (const juce::File& file)
{
    const auto extension = file.getFileExtension();
    return extension.isNotEmpty() && getFormatManager().findFormatForFileExtension (extension) != nullptr;
}

juce::String UploadEncoder::getSupportedWildcards()
{
    return "*.wav;*.aif;*.aiff;*.flac;*.ogg;*.mp3";
}

} // namespace snapplay::cloud
