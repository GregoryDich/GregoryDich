#include "Engine/DrumKit.h"

#include "Core/TransientDetector.h"
#include "Core/ZeroCrossing.h"

#include <algorithm>
#include <cmath>

namespace snapplay::engine
{

namespace
{
    constexpr int maxPadChannels = 2;
    constexpr float trimThreshold = 0.001f;   ///< -60 dBFS, as StemSound::BuildOptions::trimThreshold

    int secondsToSamples (double seconds, double sampleRate, int limit) noexcept
    {
        if (! std::isfinite (seconds))
            return 0;

        const double samples = std::round (seconds * sampleRate);
        return static_cast<int> (juce::jlimit (0.0, static_cast<double> (limit), samples));
    }

    juce::AudioBuffer<float> mixToMono (const juce::AudioBuffer<float>& source, int numChannels, int start, int length)
    {
        juce::AudioBuffer<float> mono (1, length);
        mono.clear();

        for (int channel = 0; channel < numChannels; ++channel)
            mono.addFrom (0, 0, source, channel, start, length, 1.0f / static_cast<float> (numChannels));

        return mono;
    }
} // namespace

std::shared_ptr<const DrumKit> DrumKit::build (const juce::AudioBuffer<float>& source, double sampleRateToUse,
                                               const std::vector<core::Slice>& slices, bool trimToZeroCrossings)
{
    const int sourceLength = source.getNumSamples();
    const int sourceChannels = source.getNumChannels();

    if (sourceLength <= 0 || sourceChannels <= 0 || sampleRateToUse <= 0.0 || slices.empty())
        return nullptr;

    const int numChannels = juce::jmin (maxPadChannels, sourceChannels);

    std::shared_ptr<DrumKit> kit (new DrumKit());
    kit->sampleRate = sampleRateToUse;
    kit->numChannels = numChannels;
    kit->pads.reserve (slices.size());

    for (const auto& slice : slices)
    {
        if (slice.midiNote < 0 || slice.midiNote > 127)
            continue;

        int start = secondsToSamples (slice.startSeconds, sampleRateToUse, sourceLength);
        int end = secondsToSamples (slice.endSeconds, sampleRateToUse, sourceLength);

        if (end <= start)
            continue;

        if (trimToZeroCrossings)
        {
            const int length = end - start;
            const auto mono = mixToMono (source, numChannels, start, length);
            const auto range = core::findTrimRange (mono.getReadPointer (0), length, trimThreshold);
            const int trimmedStart = start + juce::jlimit (0, length, range.start);
            const int trimmedEnd = start + juce::jlimit (0, length, range.end);

            if (trimmedEnd <= trimmedStart)
                continue;

            start = trimmedStart;
            end = trimmedEnd;
        }

        Pad pad;
        pad.midiNote = slice.midiNote;
        pad.startSeconds = static_cast<double> (start) / sampleRateToUse;
        pad.endSeconds = static_cast<double> (end) / sampleRateToUse;
        pad.audio.setSize (numChannels, end - start);

        for (int channel = 0; channel < numChannels; ++channel)
            pad.audio.copyFrom (channel, 0, source, channel, start, end - start);

        kit->pads.push_back (std::move (pad));
    }

    if (kit->pads.empty())
        return nullptr;

    auto& pads = kit->pads;
    std::stable_sort (pads.begin(), pads.end(),
                      [] (const Pad& a, const Pad& b) { return a.midiNote < b.midiNote; });

    // padForNote() must be unambiguous: the first slice wins when a note is repeated.
    pads.erase (std::unique (pads.begin(), pads.end(),
                             [] (const Pad& a, const Pad& b) { return a.midiNote == b.midiNote; }),
                pads.end());

    return kit;
}

std::shared_ptr<const DrumKit> DrumKit::buildFromTransients (const juce::AudioBuffer<float>& source, double sampleRateToUse,
                                                             const std::vector<double>& transientsSeconds,
                                                             int firstMidiNote, bool trimToZeroCrossings)
{
    const int sourceLength = source.getNumSamples();
    const int sourceChannels = source.getNumChannels();

    if (sourceLength <= 0 || sourceChannels <= 0 || sampleRateToUse <= 0.0)
        return nullptr;

    std::vector<double> onsets = transientsSeconds;

    if (onsets.empty())
    {
        const auto mono = mixToMono (source, juce::jmin (maxPadChannels, sourceChannels), 0, sourceLength);
        onsets = core::detectTransients (mono.getReadPointer (0), sourceLength, sampleRateToUse);
    }

    const double durationSeconds = static_cast<double> (sourceLength) / sampleRateToUse;
    auto slices = core::slicesFromTransients (onsets, durationSeconds, firstMidiNote);

    if (slices.empty())
    {
        // Nothing to cut: the whole stem becomes a single pad so drum mode still plays.
        core::Slice whole;
        whole.startSeconds = 0.0;
        whole.endSeconds = durationSeconds;
        whole.midiNote = juce::jlimit (0, 127, firstMidiNote);
        slices.push_back (whole);
    }

    return build (source, sampleRateToUse, slices, trimToZeroCrossings);
}

const DrumKit::Pad* DrumKit::padForNote (int midiNote) const noexcept
{
    for (const auto& pad : pads)
        if (pad.midiNote == midiNote)
            return &pad;

    return nullptr;
}

int DrumKit::getLowestNote() const noexcept
{
    return pads.empty() ? -1 : pads.front().midiNote;
}

int DrumKit::getHighestNote() const noexcept
{
    return pads.empty() ? -1 : pads.back().midiNote;
}

} // namespace snapplay::engine
