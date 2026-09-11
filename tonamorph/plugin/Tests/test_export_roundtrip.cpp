#include "TestFramework.h"

#include "Core/FscWriter.h"
#include "Core/MidiFileWriter.h"

#include <cstdint>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <sstream>
#include <string>
#include <vector>

/*
 * Exercises both writers on one fixture. When TONAMORPH_TEST_OUT names a directory, the
 * files sample.mid, sample.fsc and fixture.json are written there for Tests/roundtrip.py,
 * which re-reads them with mido and pyflp.
 */

namespace
{

using tonamorph::core::Note;
using tonamorph::core::Track;

constexpr double fixtureBpm = 124.0;

std::vector<Track> makeFixture()
{
    Track bass;
    bass.name = "bass";
    bass.channel = 0;
    bass.notes = {
        Note { .startSeconds = 0.0,  .durationSeconds = 0.5,  .pitch = 36, .velocity = 100 },
        Note { .startSeconds = 0.5,  .durationSeconds = 0.25, .pitch = 38, .velocity = 90 },
        Note { .startSeconds = 0.75, .durationSeconds = 0.25, .pitch = 36, .velocity = 110 },
        Note { .startSeconds = 1.0,  .durationSeconds = 0.5,  .pitch = 36, .velocity = 80 },   // retrigger at the previous note's end
    };

    Track other;
    other.name = "other";
    other.channel = 1;
    other.notes = {
        Note { .startSeconds = 0.125, .durationSeconds = 0.375, .pitch = 60, .velocity = 96 },
        Note { .startSeconds = 1.25,  .durationSeconds = 0.5,   .pitch = 64, .velocity = 64 },
        // Tick fields set: the .mid uses them (1.0 s / 0.25 s at 124 BPM), the .fsc uses the seconds.
        Note { .startSeconds = 2.0, .durationSeconds = 0.25, .startTicks = 992, .durationTicks = 248, .pitch = 67, .velocity = 127 },
    };

    return { bass, other };
}

std::string fixtureJson (const std::vector<Track>& tracks)
{
    std::ostringstream json;
    json << std::fixed << std::setprecision (6);
    json << "{\n  \"bpm\": " << fixtureBpm << ",\n  \"midi_ppq\": 480,\n  \"fsc_ppq\": 96,\n"
         << "  \"fl_version\": \"" << tonamorph::core::fscVersionText << "\",\n  \"tracks\": [\n";

    for (std::size_t t = 0; t < tracks.size(); ++t)
    {
        json << "    {\"name\": \"" << tracks[t].name << "\", \"channel\": " << tracks[t].channel << ", \"notes\": [\n";

        for (std::size_t n = 0; n < tracks[t].notes.size(); ++n)
        {
            const Note& note = tracks[t].notes[n];
            json << "      {\"start_seconds\": " << note.startSeconds << ", \"duration_seconds\": " << note.durationSeconds
                 << ", \"start_ticks\": " << note.startTicks << ", \"duration_ticks\": " << note.durationTicks
                 << ", \"pitch\": " << note.pitch << ", \"velocity\": " << note.velocity << "}"
                 << (n + 1 < tracks[t].notes.size() ? ",\n" : "\n");
        }

        json << "    ]}" << (t + 1 < tracks.size() ? ",\n" : "\n");
    }

    json << "  ]\n}\n";
    return json.str();
}

bool writeFile (const std::filesystem::path& path, const std::vector<std::uint8_t>& bytes)
{
    std::ofstream stream (path, std::ios::binary);
    stream.write (reinterpret_cast<const char*> (bytes.data()), static_cast<std::streamsize> (bytes.size()));
    return stream.good();
}

bool writeFile (const std::filesystem::path& path, const std::string& text)
{
    std::ofstream stream (path, std::ios::binary);
    stream << text;
    return stream.good();
}

} // namespace

TONAMORPH_TEST(exportFixtureWritesBothFormats)
{
    const auto tracks = makeFixture();
    const auto midi = tonamorph::core::writeMidiFile (tracks, fixtureBpm);
    const auto fsc = tonamorph::core::writeFsc (tracks, fixtureBpm);

    TONAMORPH_CHECK (midi.size() > 14 && std::string (midi.begin(), midi.begin() + 4) == "MThd");
    TONAMORPH_CHECK (fsc.size() > 22 && std::string (fsc.begin(), fsc.begin() + 4) == "FLhd");

    const char* outDir = std::getenv ("TONAMORPH_TEST_OUT");
    if (outDir == nullptr || *outDir == '\0')
        return;

    const std::filesystem::path directory (outDir);
    std::error_code error;
    std::filesystem::create_directories (directory, error);
    TONAMORPH_CHECK (! error);

    TONAMORPH_CHECK (writeFile (directory / "sample.mid", midi));
    TONAMORPH_CHECK (writeFile (directory / "sample.fsc", fsc));
    TONAMORPH_CHECK (writeFile (directory / "fixture.json", fixtureJson (tracks)));
}
