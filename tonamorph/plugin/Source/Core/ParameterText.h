#pragma once

/**
 * Text ↔ value conversion for the host-visible parameters and the knob text boxes
 * (the AudioParameterFloat / AudioParameterInt string converters): "2.0 ms", "120 ms",
 * "1.20 s", "80 %", "-6.0 dB" ("-inf dB" at the silence floor), "250 Hz", "1.25 kHz",
 * "0.71" and note names such as "C3" (middle C = C4). Parsing is tolerant: units are
 * optional and case-insensitive, "1.2 s" and "2k" are accepted, and anything unreadable
 * is nullopt. Standard-library only so every case is unit-tested without JUCE.
 */

#include <array>
#include <cmath>
#include <cstddef>
#include <optional>
#include <string>
#include <string_view>
#include <utility>

namespace tonamorph::core
{

/** Sharp spellings, index = pitch class. */
inline constexpr std::array<const char*, 12> noteNames {
    "C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"
};

namespace detail
{
    /** Fixed-point formatting that ignores the C locale (a host may have set a comma
        decimal separator) and never prints "-0.0". */
    inline std::string formatFixed (double value, int decimals)
    {
        long long scale = 1;

        for (int i = 0; i < decimals; ++i)
            scale *= 10;

        const auto scaled = std::llround (value * static_cast<double> (scale));
        const auto magnitude = scaled < 0 ? -scaled : scaled;
        std::string text = scaled < 0 ? "-" : "";
        text += std::to_string (magnitude / scale);

        if (decimals > 0)
        {
            auto fraction = std::to_string (magnitude % scale);
            text += '.';
            text += std::string (static_cast<std::size_t> (decimals) - fraction.size(), '0');
            text += fraction;
        }

        return text;
    }

    inline std::string_view trim (std::string_view text) noexcept
    {
        auto isSpace = [] (unsigned char c) { return c == ' ' || c == '\t' || c == '\n' || c == '\r'; };

        while (! text.empty() && isSpace (static_cast<unsigned char> (text.front())))
            text.remove_prefix (1);

        while (! text.empty() && isSpace (static_cast<unsigned char> (text.back())))
            text.remove_suffix (1);

        return text;
    }

    inline std::string lower (std::string_view text)
    {
        std::string out (text);

        for (auto& c : out)
            if (c >= 'A' && c <= 'Z')
                c = static_cast<char> (c - 'A' + 'a');

        return out;
    }

    /** Reads `[+-]digits[.digits]` from the start of `text` (locale-independent, no
        exponent); nullopt without at least one digit. `consumed` receives the length. */
    inline std::optional<double> leadingDecimal (std::string_view text, std::size_t& consumed) noexcept
    {
        std::size_t pos = 0;
        bool negative = false;

        if (pos < text.size() && (text[pos] == '-' || text[pos] == '+'))
            negative = text[pos++] == '-';

        double value = 0.0;
        int digits = 0;

        while (pos < text.size() && text[pos] >= '0' && text[pos] <= '9')
        {
            value = value * 10.0 + (text[pos++] - '0');
            ++digits;
        }

        if (pos < text.size() && (text[pos] == '.' || text[pos] == ','))
        {
            double scale = 0.1;
            ++pos;

            while (pos < text.size() && text[pos] >= '0' && text[pos] <= '9')
            {
                value += (text[pos++] - '0') * scale;
                scale *= 0.1;
                ++digits;
            }
        }

        if (digits == 0)
            return std::nullopt;

        consumed = pos;
        return negative ? -value : value;
    }

    /** Splits "-6.5 dB" into the number and the lower-cased unit ("db"); nullopt when the
        text does not start with a number. */
    inline std::optional<std::pair<double, std::string>> numberAndUnit (std::string_view text)
    {
        const auto trimmed = trim (text);
        std::size_t consumed = 0;
        const auto value = leadingDecimal (trimmed, consumed);

        if (! value.has_value())
            return std::nullopt;

        return std::make_pair (*value, lower (trim (trimmed.substr (consumed))));
    }
} // namespace detail

//==============================================================================
// Milliseconds (attack, decay, release)

inline std::string formatMilliseconds (double milliseconds)
{
    if (milliseconds >= 999.5)
        return detail::formatFixed (milliseconds / 1000.0, 2) + " s";

    if (milliseconds < 9.95)
        return detail::formatFixed (milliseconds, 1) + " ms";

    return detail::formatFixed (milliseconds, 0) + " ms";
}

inline std::optional<double> parseMilliseconds (std::string_view text)
{
    const auto parsed = detail::numberAndUnit (text);

    if (! parsed.has_value())
        return std::nullopt;

    const auto& [value, unit] = *parsed;

    if (unit.empty() || unit == "ms")
        return value;

    if (unit == "s" || unit == "sec")
        return value * 1000.0;

    return std::nullopt;
}

//==============================================================================
// Percent (sustain: 0..1 shown as 0..100 %)

inline std::string formatPercent (double fraction)
{
    return detail::formatFixed (fraction * 100.0, 0) + " %";
}

/** "80 %" → 0.8, "80" → 0.8, "0.8" → 0.8 (a bare number above 1 is read as a percentage). */
inline std::optional<double> parsePercent (std::string_view text)
{
    const auto parsed = detail::numberAndUnit (text);

    if (! parsed.has_value())
        return std::nullopt;

    const auto& [value, unit] = *parsed;

    if (unit == "%")
        return value / 100.0;

    if (unit.empty())
        return value > 1.0 ? value / 100.0 : value;

    return std::nullopt;
}

//==============================================================================
// Decibels (gain), with a silence floor

inline std::string formatDecibels (double decibels, double floorDb)
{
    if (decibels <= floorDb)
        return "-inf dB";

    return detail::formatFixed (decibels, 1) + " dB";
}

inline std::optional<double> parseDecibels (std::string_view text, double floorDb)
{
    const auto lowered = detail::lower (detail::trim (text));

    if (lowered == "-inf" || lowered == "-inf db" || lowered == "-infinity")
        return floorDb;

    const auto parsed = detail::numberAndUnit (text);

    if (! parsed.has_value())
        return std::nullopt;

    const auto& [value, unit] = *parsed;

    if (unit.empty() || unit == "db")
        return value;

    return std::nullopt;
}

//==============================================================================
// Hertz (filter cutoff)

inline std::string formatHertz (double hertz)
{
    if (hertz < 999.5)
        return detail::formatFixed (hertz, 0) + " Hz";

    if (hertz < 9999.5)
        return detail::formatFixed (hertz / 1000.0, 2) + " kHz";

    return detail::formatFixed (hertz / 1000.0, 1) + " kHz";
}

inline std::optional<double> parseHertz (std::string_view text)
{
    const auto parsed = detail::numberAndUnit (text);

    if (! parsed.has_value())
        return std::nullopt;

    const auto& [value, unit] = *parsed;

    if (unit.empty() || unit == "hz")
        return value;

    if (unit == "k" || unit == "khz")
        return value * 1000.0;

    return std::nullopt;
}

//==============================================================================
// Plain ratio (filter resonance / Q)

inline std::string formatRatio (double value)
{
    return detail::formatFixed (value, 2);
}

inline std::optional<double> parseRatio (std::string_view text)
{
    const auto parsed = detail::numberAndUnit (text);

    if (! parsed.has_value() || ! parsed->second.empty())
        return std::nullopt;

    return parsed->first;
}

//==============================================================================
// Note names (root target, scale root)

/** "C3" for 48, "A#4" for 70; middle C (60) is C4. Out-of-range notes are clamped. */
inline std::string formatNoteName (int midiNote)
{
    const int note = midiNote < 0 ? 0 : (midiNote > 127 ? 127 : midiNote);
    return std::string (noteNames[static_cast<std::size_t> (note % 12)]) + std::to_string (note / 12 - 1);
}

/** "C", "C#", ... "B" for a pitch class (any integer is reduced modulo 12). */
inline std::string formatPitchClassName (int pitchClass)
{
    return noteNames[static_cast<std::size_t> (((pitchClass % 12) + 12) % 12)];
}

/** Accepts "C3", "f#2", "Bb1", " A 4 " or a plain MIDI number; nullopt otherwise. */
inline std::optional<int> parseNoteName (std::string_view text)
{
    const std::string trimmed = detail::lower (detail::trim (text));

    if (trimmed.empty())
        return std::nullopt;

    if (trimmed[0] >= '0' && trimmed[0] <= '9')
    {
        const auto parsed = detail::numberAndUnit (trimmed);

        if (! parsed.has_value() || ! parsed->second.empty())
            return std::nullopt;

        return static_cast<int> (std::lround (parsed->first));
    }

    const auto letterIndex = std::string_view ("c d ef g a b").find (trimmed[0]);

    if (letterIndex == std::string_view::npos || trimmed[0] == ' ')
        return std::nullopt;

    int pitchClass = static_cast<int> (letterIndex);
    std::size_t pos = 1;

    if (pos < trimmed.size() && trimmed[pos] == '#')
    {
        ++pitchClass;
        ++pos;
    }
    else if (pos < trimmed.size() && trimmed[pos] == 'b')
    {
        --pitchClass;
        ++pos;
    }

    const auto octaveText = detail::trim (std::string_view (trimmed).substr (pos));

    if (octaveText.empty())
        return std::nullopt;

    const auto octave = detail::numberAndUnit (octaveText);

    if (! octave.has_value() || ! octave->second.empty())
        return std::nullopt;

    return (static_cast<int> (std::lround (octave->first)) + 1) * 12 + pitchClass;
}

/** Same as parseNoteName() for a pitch class: "F#" → 6, "Bb" → 10, "3" → 3. */
inline std::optional<int> parsePitchClassName (std::string_view text)
{
    const std::string trimmed = detail::lower (detail::trim (text));

    if (trimmed.empty())
        return std::nullopt;

    if (trimmed[0] >= '0' && trimmed[0] <= '9')
    {
        const auto parsed = detail::numberAndUnit (trimmed);

        if (! parsed.has_value() || ! parsed->second.empty())
            return std::nullopt;

        return static_cast<int> (std::lround (parsed->first)) % 12;
    }

    const auto note = parseNoteName (trimmed + "0");   // octave-less names borrow octave 0
    return note.has_value() ? std::optional<int> (((*note % 12) + 12) % 12) : std::nullopt;
}

} // namespace tonamorph::core
