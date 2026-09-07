#include "Engine/ScaleLockProcessor.h"

namespace snapplay::engine
{

ScaleLockProcessor::ScaleLockProcessor()
{
    reset();
}

void ScaleLockProcessor::prepare()
{
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
    if (midi.isEmpty())
        return;

    const auto mask = activeMask.load (std::memory_order_acquire);

    // Snapping only rewrites the note-number byte of an existing message, so the events are
    // edited where they lie: no second buffer, no copying, no allocation, and every event
    // keeps its order and timestamp (including negative sample positions).
    for (const auto metadata : midi)
    {
        if (metadata.numBytes != 3)
            continue;

        const auto* data = metadata.data;
        const int status = data[0] & 0xF0;
        const auto channel = static_cast<size_t> (data[0] & 0x0F);
        const auto note = static_cast<size_t> (data[1] & 0x7F);
        const int value = data[2] & 0x7F;
        const bool noteOn = status == 0x90 && value > 0;
        const bool noteOff = status == 0x80 || (status == 0x90 && value == 0);
        const bool aftertouch = status == 0xA0;

        if (! (noteOn || noteOff || aftertouch))
            continue;

        auto& held = heldPitch[channel][note];

        // A held note keeps its pitch for retriggers, note-off and aftertouch even if the
        // scale changed meanwhile; anything else follows the current mask.
        const int pitch = held != notHeld ? static_cast<int> (held)
                                          : core::snapToMask (static_cast<int> (note), mask);

        if (noteOn)
            held = static_cast<std::int8_t> (pitch);
        else if (noteOff)
            held = notHeld;

        // The buffer itself is non-const; the iterator is the only thing that adds the
        // qualifier. Writing back one byte of an equally sized message never moves storage.
        const_cast<juce::uint8*> (data)[1] = static_cast<juce::uint8> (pitch);
    }
}

void ScaleLockProcessor::reset() noexcept
{
    for (auto& channel : heldPitch)
        channel.fill (notHeld);
}

} // namespace snapplay::engine
