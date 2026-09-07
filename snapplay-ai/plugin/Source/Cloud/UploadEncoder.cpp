#include "Cloud/UploadEncoder.h"

namespace snapplay::cloud
{

UploadEncoder::Result UploadEncoder::encodeFile (const juce::File& file)
{
    Result result;
    result.errorMessage = "Not implemented: " + file.getFileName();
    return result;
}

UploadEncoder::Result UploadEncoder::encodeBuffer (const juce::AudioBuffer<float>& audio, double sourceSampleRate)
{
    juce::ignoreUnused (audio, sourceSampleRate);
    Result result;
    result.errorMessage = "Not implemented";
    return result;
}

bool UploadEncoder::isSupportedFile (const juce::File& file)
{
    juce::ignoreUnused (file);
    return false;
}

juce::String UploadEncoder::getSupportedWildcards()
{
    return "*.wav;*.aif;*.aiff;*.flac;*.ogg;*.mp3";
}

} // namespace snapplay::cloud
