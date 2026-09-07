#include "Engine/DrumKit.h"

#include "Core/TransientDetector.h"
#include "Core/ZeroCrossing.h"

namespace snapplay::engine
{

std::shared_ptr<const DrumKit> DrumKit::build (const juce::AudioBuffer<float>& source, double sampleRateToUse,
                                               const std::vector<core::Slice>& slices, bool trimToZeroCrossings)
{
    juce::ignoreUnused (source, sampleRateToUse, slices, trimToZeroCrossings);
    return nullptr;
}

std::shared_ptr<const DrumKit> DrumKit::buildFromTransients (const juce::AudioBuffer<float>& source, double sampleRateToUse,
                                                             const std::vector<double>& transientsSeconds,
                                                             int firstMidiNote, bool trimToZeroCrossings)
{
    juce::ignoreUnused (source, sampleRateToUse, transientsSeconds, firstMidiNote, trimToZeroCrossings);
    return nullptr;
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
