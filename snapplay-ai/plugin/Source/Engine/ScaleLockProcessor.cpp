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
    if (midi.isEmpty())
        return;

    const auto mask = activeMask.load (std::memory_order_acquire);

    // Rewritten events have the same byte size as the originals, so copying them back into
    // `midi` after clear() (which keeps its storage) never grows either buffer.
    scratch.clear();

    for (const auto metadata : midi)
    {
        const auto* data = metadata.data;

        if (metadata.numBytes == 3)
        {
            const int status = data[0] & 0xF0;
            const auto channel = static_cast<size_t> (data[0] & 0x0F);
            const auto note = static_cast<size_t> (data[1] & 0x7F);
            const int value = data[2] & 0x7F;
            const bool noteOn = status == 0x90 && value > 0;
            const bool noteOff = status == 0x80 || (status == 0x90 && value == 0);
            const bool aftertouch = status == 0xA0;

            if (noteOn || noteOff || aftertouch)
            {
                auto& held = heldPitch[channel][note];

                // A held note keeps its pitch for retriggers, note-off and aftertouch even if
                // the scale changed meanwhile; anything else follows the current mask.
                const int pitch = held != notHeld ? static_cast<int> (held)
                                                  : core::snapToMask (static_cast<int> (note), mask);

                if (noteOn)
                    held = static_cast<std::int8_t> (pitch);
                else if (noteOff)
                    held = notHeld;

                const juce::uint8 message[3] = { data[0], static_cast<juce::uint8> (pitch), data[2] };
                scratch.addEvent (message, 3, metadata.samplePosition);
                continue;
            }
        }

        scratch.addEvent (data, metadata.numBytes, metadata.samplePosition);
    }

    midi.clear();
    midi.addEvents (scratch, 0, -1, 0);
}

void ScaleLockProcessor::reset() noexcept
{
    for (auto& channel : heldPitch)
        channel.fill (notHeld);
}

} // namespace snapplay::engine
