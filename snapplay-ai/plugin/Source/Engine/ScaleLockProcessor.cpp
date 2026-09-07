#include "Engine/ScaleLockProcessor.h"

namespace snapplay::engine
{

ScaleLockProcessor::ScaleLockProcessor()
{
    reset();
}

void ScaleLockProcessor::prepare (int maximumEvents)
{
    scratch.ensureSize (static_cast<size_t> (juce::jmax (1, maximumEvents)) * 8u);
    reset();
}

void ScaleLockProcessor::setDetectedScale (const std::vector<int>& pitchClasses)
{
    model.setScale (pitchClasses);
    activeMask.store (model.getMask(), std::memory_order_release);
}

void ScaleLockProcessor::setMode (core::ScaleMode mode, int rootPitchClass)
{
    model.setMode (mode, rootPitchClass);
    activeMask.store (model.getMask(), std::memory_order_release);
}

void ScaleLockProcessor::process (juce::MidiBuffer& midi)
{
    juce::ignoreUnused (midi);
}

void ScaleLockProcessor::reset() noexcept
{
    for (auto& channel : heldPitch)
        channel.fill (notHeld);
}

} // namespace snapplay::engine
