#pragma once

/**
 * An immutable set of one-shot pads: each drum slice (contract §2 `slices[]`, or slices
 * derived locally from transients per §8) becomes a sample mapped to one MIDI note.
 *
 * Built off the audio thread; afterwards every accessor is const, lock-free and
 * allocation-free.
 */

#include <JuceHeader.h>

#include "Core/Types.h"

#include <memory>
#include <vector>

namespace tonamorph::engine
{

class DrumKit
{
public:
    struct Pad
    {
        int midiNote = 36;
        double startSeconds = 0.0;        ///< position in the source stem
        double endSeconds = 0.0;
        juce::AudioBuffer<float> audio;   ///< the slice, trimmed at zero crossings
    };

    /** Cuts `source` into pads from the server's slices. Slices outside the buffer are
        clipped; empty slices are dropped. Returns nullptr when no pad survives. */
    static std::shared_ptr<const DrumKit> build (const juce::AudioBuffer<float>& source, double sampleRate,
                                                 const std::vector<core::Slice>& slices,
                                                 bool trimToZeroCrossings = true);

    /** Slices locally: core::slicesFromTransients (transientsSeconds, duration, firstMidiNote);
        when `transientsSeconds` is empty, core::detectTransients runs on a mono mixdown first. */
    static std::shared_ptr<const DrumKit> buildFromTransients (const juce::AudioBuffer<float>& source, double sampleRate,
                                                               const std::vector<double>& transientsSeconds,
                                                               int firstMidiNote = 36,
                                                               bool trimToZeroCrossings = true);

    //==============================================================================
    double getSampleRate() const noexcept { return sampleRate; }
    int getNumChannels() const noexcept { return numChannels; }
    int getNumPads() const noexcept { return static_cast<int> (pads.size()); }
    const std::vector<Pad>& getPads() const noexcept { return pads; }
    /** The pad mapped to `midiNote`, or nullptr. Lock-free. */
    const Pad* padForNote (int midiNote) const noexcept;
    int getLowestNote() const noexcept;
    int getHighestNote() const noexcept;

private:
    DrumKit() = default;

    double sampleRate = 44100.0;
    int numChannels = 2;
    std::vector<Pad> pads;   ///< sorted by midiNote
};

} // namespace tonamorph::engine
