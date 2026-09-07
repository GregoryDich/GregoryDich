#pragma once

/**
 * Realtime Scale-Snap (contract §8) applied to the incoming juce::MidiBuffer.
 *
 * The message thread selects the mode/root/detected scale; the active pitch-class set is
 * published to the audio thread as one atomic 12-bit mask. process() rewrites note-ons to
 * the snapped pitch in place and remembers the mapping per channel so the matching
 * note-off uses the same pitch even if the mode changed while the note was held. It never
 * allocates: only the note-number byte of an existing message changes.
 */

#include <JuceHeader.h>

#include "Core/ScaleLock.h"
#include "Core/Types.h"

#include <array>
#include <atomic>
#include <cstdint>
#include <vector>

namespace snapplay::engine
{

class ScaleLockProcessor
{
public:
    ScaleLockProcessor();

    /** Clears the held-note map; call from prepareToPlay. process() needs no per-block
        storage, so there is nothing else to prepare. */
    void prepare();

    //==============================================================================
    /** Message thread: installs `analysis.key.scale_pitch_classes`. */
    void setDetectedScale (const std::vector<int>& pitchClasses);
    /** Message thread (or parameter callback): selects mode and root (0..11). */
    void setMode (core::ScaleMode mode, int rootPitchClass);
    core::ScaleMode getMode() const noexcept { return model.getMode(); }
    int getRootPitchClass() const noexcept { return model.getRootPitchClass(); }
    /** Message-thread view of the active set. */
    const core::ScaleLock& getModel() const noexcept { return model; }
    /** The mask the audio thread is using right now. */
    std::uint16_t getActiveMask() const noexcept { return activeMask.load (std::memory_order_acquire); }
    bool isPassthrough() const noexcept { return (getActiveMask() & 0x0FFFu) == 0; }

    //==============================================================================
    /** Audio thread: snaps note-ons/offs in place (other events pass through untouched,
        order and timestamps preserved). */
    void process (juce::MidiBuffer& midi);
    /** Audio thread: forgets held notes (call from prepareToPlay / on reset). */
    void reset() noexcept;

private:
    static constexpr std::int8_t notHeld = -1;

    core::ScaleLock model;                                     ///< message thread only
    std::atomic<std::uint16_t> activeMask { 0 };
    std::array<std::array<std::int8_t, 128>, 16> heldPitch;   ///< [channel-1][originalNote] = snapped pitch or notHeld

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR (ScaleLockProcessor)
};

} // namespace snapplay::engine
