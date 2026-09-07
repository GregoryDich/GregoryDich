#pragma once

/**
 * Plain data types shared by the JUCE-free core algorithms and the plugin.
 *
 * Everything in snapplay::core depends on the C++ standard library only, so the
 * Tests/ target can compile it without a JUCE include path.
 */

#include <cmath>
#include <limits>
#include <string>
#include <vector>

namespace snapplay::core
{

/** One transcribed note (contract §2, JobResult.midi.tracks[].notes[]).
    Seconds are authoritative; ticks are expressed at the PPQ the server used (480). */
struct Note
{
    double startSeconds = 0.0;
    double durationSeconds = 0.0;
    int startTicks = 0;
    int durationTicks = 0;
    int pitch = 60;        ///< MIDI note number 0..127
    int velocity = 100;    ///< 1..127
};

/** One MIDI track: a transcribed stem (contract §2, JobResult.midi.tracks[]). */
struct Track
{
    std::string name;      ///< Stem name: bass | drums | other | vocals
    int channel = 0;       ///< MIDI channel 0..15
    std::vector<Note> notes;
};

/** Amplitude envelope in the units used by the contract (`suggested_adsr`). */
struct Adsr
{
    double attackMs = 2.0;
    double decayMs = 120.0;
    double sustain = 0.8;   ///< 0..1, fraction of peak
    double releaseMs = 180.0;
};

/** Detected key (contract §2, JobResult.analysis.key). */
struct KeyInfo
{
    std::string root;                     ///< e.g. "F"
    std::string mode;                     ///< "major" | "minor"
    int rootMidi = 60;                    ///< MIDI note of the tonic in the detected octave
    double confidence = 0.0;              ///< 0..1
    std::vector<int> scalePitchClasses;   ///< pitch classes 0..11 of the detected scale
};

/** One drum slice mapped to a MIDI note (contract §2, stems[].slices[]). */
struct Slice
{
    double startSeconds = 0.0;
    double endSeconds = 0.0;
    int midiNote = 36;     ///< C1 for the first slice, incrementing
};

/** Scale-Snap pitch-class set selector (contract §8). Order matches the `scaleMode`
    parameter choices: Detected, Major, Minor, PentatonicMajor, PentatonicMinor, Off. */
enum class ScaleMode
{
    Detected = 0,
    Major,
    Minor,
    PentatonicMajor,
    PentatonicMinor,
    Off
};

/** Number of ScaleMode enumerators (the size of the `scaleMode` choice parameter). */
inline constexpr int numScaleModes = 6;

/** Returns the contract §8 identifier for a mode ("detected", "major", ... "off"). */
inline const char* scaleModeToString (ScaleMode mode) noexcept
{
    switch (mode)
    {
        case ScaleMode::Detected:        return "detected";
        case ScaleMode::Major:           return "major";
        case ScaleMode::Minor:           return "minor";
        case ScaleMode::PentatonicMajor: return "pentatonic_major";
        case ScaleMode::PentatonicMinor: return "pentatonic_minor";
        case ScaleMode::Off:             return "off";
    }

    return "off";
}

/**
 * Contract timing rule shared by the exporters: `ticks = round (seconds * bpm / 60 * ppq)`.
 * Non-finite or negative seconds yield 0; the result saturates at INT_MAX.
 */
inline int secondsToTicks (double seconds, double bpm, int ppq) noexcept
{
    if (! std::isfinite (seconds) || seconds <= 0.0)
        return 0;

    const double ticks = std::round (seconds * bpm / 60.0 * static_cast<double> (ppq));

    if (! (ticks < static_cast<double> (std::numeric_limits<int>::max())))
        return std::numeric_limits<int>::max();

    return ticks > 0.0 ? static_cast<int> (ticks) : 0;
}

} // namespace snapplay::core
