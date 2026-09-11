#include "TestFramework.h"

#include <cctype>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <sstream>
#include <string>

// The bundled demo morph is generated at configure time (Resources/generate_demo.py) in
// the plugin's cache/result format. This validates its JSON syntax with a small strict
// parser, checks the fields the processor relies on, and bounds the embedded size.

namespace
{
    class JsonValidator
    {
    public:
        explicit JsonValidator(const std::string& textToParse) : text(textToParse) {}

        bool validate()
        {
            skipSpace();
            if (!value())
                return false;
            skipSpace();
            return pos == text.size();
        }

    private:
        bool value()
        {
            if (pos >= text.size())
                return false;

            const char c = text[pos];
            if (c == '{') return object();
            if (c == '[') return array();
            if (c == '"') return string();
            if (c == 't') return literal("true");
            if (c == 'f') return literal("false");
            if (c == 'n') return literal("null");
            return number();
        }

        bool object()
        {
            ++pos;
            skipSpace();
            if (peek() == '}') { ++pos; return true; }

            for (;;)
            {
                skipSpace();
                if (!string()) return false;
                skipSpace();
                if (peek() != ':') return false;
                ++pos;
                skipSpace();
                if (!value()) return false;
                skipSpace();
                if (peek() == ',') { ++pos; continue; }
                if (peek() == '}') { ++pos; return true; }
                return false;
            }
        }

        bool array()
        {
            ++pos;
            skipSpace();
            if (peek() == ']') { ++pos; return true; }

            for (;;)
            {
                skipSpace();
                if (!value()) return false;
                skipSpace();
                if (peek() == ',') { ++pos; continue; }
                if (peek() == ']') { ++pos; return true; }
                return false;
            }
        }

        bool string()
        {
            if (peek() != '"') return false;
            ++pos;

            while (pos < text.size())
            {
                const char c = text[pos++];
                if (c == '"') return true;
                if (c == '\\')
                {
                    if (pos >= text.size()) return false;
                    const char e = text[pos++];
                    if (e == 'u')
                    {
                        for (int i = 0; i < 4; ++i)
                            if (pos >= text.size() || !std::isxdigit(static_cast<unsigned char>(text[pos++])))
                                return false;
                    }
                    else if (std::string("\"\\/bfnrt").find(e) == std::string::npos)
                        return false;
                }
                else if (static_cast<unsigned char>(c) < 0x20)
                    return false;
            }

            return false;
        }

        bool number()
        {
            const auto start = pos;
            if (peek() == '-') ++pos;
            if (!std::isdigit(static_cast<unsigned char>(peek()))) return false;
            while (std::isdigit(static_cast<unsigned char>(peek()))) ++pos;
            if (peek() == '.')
            {
                ++pos;
                if (!std::isdigit(static_cast<unsigned char>(peek()))) return false;
                while (std::isdigit(static_cast<unsigned char>(peek()))) ++pos;
            }
            if (peek() == 'e' || peek() == 'E')
            {
                ++pos;
                if (peek() == '+' || peek() == '-') ++pos;
                if (!std::isdigit(static_cast<unsigned char>(peek()))) return false;
                while (std::isdigit(static_cast<unsigned char>(peek()))) ++pos;
            }
            return pos > start;
        }

        bool literal(const char* word)
        {
            const std::string expected(word);
            if (text.compare(pos, expected.size(), expected) != 0) return false;
            pos += expected.size();
            return true;
        }

        char peek() const { return pos < text.size() ? text[pos] : '\0'; }
        void skipSpace() { while (pos < text.size() && std::isspace(static_cast<unsigned char>(text[pos]))) ++pos; }

        const std::string& text;
        std::size_t pos = 0;
    };

    std::string readFile(const std::filesystem::path& path)
    {
        std::ifstream in(path, std::ios::binary);
        std::ostringstream buffer;
        buffer << in.rdbuf();
        return buffer.str();
    }

    bool contains(const std::string& text, const char* needle)
    {
        return text.find(needle) != std::string::npos;
    }
} // namespace

TONAMORPH_TEST(demoManifestParsesAndDescribesTheBundle)
{
#ifdef TONAMORPH_DEMO_DIR
    const std::filesystem::path demo(TONAMORPH_DEMO_DIR);
    TONAMORPH_CHECK(std::filesystem::is_directory(demo));

    const auto manifest = readFile(demo / "result.json");
    TONAMORPH_CHECK(!manifest.empty());
    TONAMORPH_CHECK(JsonValidator(manifest).validate());

    // Fields JobResult::fromJson requires, plus the demo marker.
    for (const char* key : { "\"job_id\": \"demo\"", "\"demo\": true", "\"credits_charged\": 0", "\"analysis\"",
                             "\"root\": \"A\"", "\"mode\": \"minor\"", "\"bpm\": 120", "\"stems\"", "\"midi\"",
                             "\"tracks\"", "\"expires_at\"", "\"scale_pitch_classes\"", "\"slices\"" })
        if (!contains(manifest, key))
            tonamorph::test::reportFailure(__FILE__, __LINE__, std::string("manifest lacks ") + key);

    std::uintmax_t totalBytes = 0;

    for (const char* name : { "bass.wav", "drums.wav", "other.wav", "vocals.wav", "score.mid", "result.json" })
    {
        const auto file = demo / name;

        if (!std::filesystem::is_regular_file(file))
        {
            tonamorph::test::reportFailure(__FILE__, __LINE__, std::string("missing demo file ") + name);
            continue;
        }

        totalBytes += std::filesystem::file_size(file);
    }

    for (const char* stem : { "\"name\": \"bass\"", "\"name\": \"drums\"", "\"name\": \"other\"", "\"name\": \"vocals\"" })
        if (!contains(manifest, stem))
            tonamorph::test::reportFailure(__FILE__, __LINE__, std::string("manifest lacks stem ") + stem);

    for (const char* name : { "bass.wav", "drums.wav", "other.wav", "vocals.wav" })
    {
        const auto wav = readFile(demo / name);
        TONAMORPH_CHECK(wav.size() > 44 && wav.compare(0, 4, "RIFF") == 0 && wav.compare(8, 4, "WAVE") == 0);
        // 44.1 kHz mono 16-bit: at most 8 s of audio.
        TONAMORPH_CHECK(wav.size() <= 44u + 8u * 44100u * 2u + 1024u);
    }

    const auto midi = readFile(demo / "score.mid");
    TONAMORPH_CHECK(midi.size() > 14 && midi.compare(0, 4, "MThd") == 0);

    TONAMORPH_CHECK(totalBytes < 1'500'000u);
#else
    tonamorph::test::reportFailure(__FILE__, __LINE__, "TONAMORPH_DEMO_DIR is not defined for the test target");
#endif
}
