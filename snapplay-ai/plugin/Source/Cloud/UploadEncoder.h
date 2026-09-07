#pragma once

/**
 * Prepares audio for `POST /v1/jobs` (contract §2): any readable input becomes a mono or
 * stereo 44.1 kHz FLAC in memory, cut to the first 60 s and kept under 10 MB.
 *
 * Pure functions; safe to call from any non-audio thread. Long inputs are truncated
 * client-side so the upload never exceeds the server cap, and the truncation is reported.
 */

#include <JuceHeader.h>

#include <cstddef>

namespace snapplay::cloud
{

class UploadEncoder
{
public:
    /** Contract limits. */
    static constexpr double maxSeconds = 60.0;
    static constexpr std::size_t maxBytes = 10u * 1024u * 1024u;
    static constexpr double targetSampleRate = 44100.0;
    static constexpr int maxChannels = 2;
    static constexpr const char* mimeType = "audio/flac";
    static constexpr const char* fileName = "input.flac";

    struct Result
    {
        juce::MemoryBlock flacData;            ///< empty on failure
        bool truncated = false;                ///< input was longer than maxSeconds
        double inputDurationSeconds = 0.0;     ///< before truncation
        double encodedDurationSeconds = 0.0;   ///< after truncation
        int sampleRate = 44100;                ///< always targetSampleRate on success
        int numChannels = 0;                   ///< 1 or 2
        juce::String errorMessage;             ///< set when ok() is false

        bool ok() const noexcept { return flacData.getSize() > 0 && errorMessage.isEmpty(); }
    };

    /** Decodes `file` with the registered formats (WAV, AIFF, FLAC, OGG, MP3 where
        available) and encodes it. Unsupported or unreadable files yield a Result with
        `errorMessage` set. */
    static Result encodeFile (const juce::File& file);

    /** Encodes an in-memory buffer (any channel count, any rate). Channels beyond two are
        mixed down; the buffer is resampled to 44.1 kHz. */
    static Result encodeBuffer (const juce::AudioBuffer<float>& audio, double sourceSampleRate);

    /** True when the file extension is one the decoder registry accepts. */
    static bool isSupportedFile (const juce::File& file);

    /** Wildcard pattern for file choosers, e.g. "*.wav;*.aif;*.aiff;*.flac;*.ogg;*.mp3". */
    static juce::String getSupportedWildcards();

private:
    UploadEncoder() = delete;
};

} // namespace snapplay::cloud
