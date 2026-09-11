#pragma once

/**
 * Request body of `POST /v1/jobs/{job_id}/feedback` (GTM Appendix B §5):
 * `{ rating: "up"|"down", reason?: bleed|wrong_key|midi_off|clicks|slow|other,
 *    note?: string ≤ 140, drop_to_ready_ms?: int }`.
 * Built as text here, standard-library only, so the exact payload is unit-tested.
 */

#include <array>
#include <cstdint>
#include <optional>
#include <string>
#include <string_view>

namespace tonamorph::core
{

inline constexpr std::size_t maxFeedbackNoteLength = 140;   ///< in Unicode code points

/** Contract reason codes, in the order the UI offers them. */
inline constexpr std::array<const char*, 6> feedbackReasons { "bleed", "wrong_key", "midi_off", "clicks", "slow", "other" };

inline bool isValidFeedbackReason (std::string_view reason) noexcept
{
    for (const auto* known : feedbackReasons)
        if (reason == known)
            return true;

    return false;
}

/** Escapes `text` for use inside a JSON string literal (quotes, backslash, control chars). */
inline std::string jsonEscape (std::string_view text)
{
    static constexpr char hex[] = "0123456789abcdef";
    std::string out;
    out.reserve (text.size() + 8);

    for (const char ch : text)
    {
        const auto c = static_cast<unsigned char> (ch);

        switch (c)
        {
            case '"':  out += "\\\""; break;
            case '\\': out += "\\\\"; break;
            case '\n': out += "\\n";  break;
            case '\r': out += "\\r";  break;
            case '\t': out += "\\t";  break;
            default:
                if (c < 0x20)
                {
                    out += "\\u00";
                    out += hex[c >> 4];
                    out += hex[c & 0x0f];
                }
                else
                {
                    out += static_cast<char> (c);
                }
        }
    }

    return out;
}

/** Trims surrounding whitespace and cuts `text` to `maxCodePoints` code points without
    splitting a UTF-8 sequence. */
inline std::string trimAndTruncate (std::string_view text, std::size_t maxCodePoints)
{
    auto isSpace = [] (unsigned char c) { return c == ' ' || c == '\t' || c == '\n' || c == '\r'; };

    while (! text.empty() && isSpace (static_cast<unsigned char> (text.front())))
        text.remove_prefix (1);

    while (! text.empty() && isSpace (static_cast<unsigned char> (text.back())))
        text.remove_suffix (1);

    std::size_t codePoints = 0;
    std::size_t bytes = 0;

    while (bytes < text.size() && codePoints < maxCodePoints)
    {
        const auto lead = static_cast<unsigned char> (text[bytes]);
        std::size_t length = 1;

        if ((lead & 0xe0) == 0xc0)      length = 2;
        else if ((lead & 0xf0) == 0xe0) length = 3;
        else if ((lead & 0xf8) == 0xf0) length = 4;

        if (bytes + length > text.size())
            break;

        bytes += length;
        ++codePoints;
    }

    return std::string (text.substr (0, bytes));
}

/** The feedback note: trimmed and cut to maxFeedbackNoteLength code points. */
inline std::string truncateFeedbackNote (std::string_view note)
{
    return trimAndTruncate (note, maxFeedbackNoteLength);
}

/**
 * The feedback JSON. `reason` and `note` are omitted when empty (an unknown reason is
 * omitted too); the note is truncated with truncateFeedbackNote().
 */
inline std::string buildFeedbackJson (bool thumbsUp, std::string_view reason, std::string_view note,
                                      std::optional<std::int64_t> dropToReadyMs)
{
    std::string json = "{\"rating\":\"";
    json += thumbsUp ? "up" : "down";
    json += '"';

    if (! reason.empty() && isValidFeedbackReason (reason))
    {
        json += ",\"reason\":\"";
        json += reason;
        json += '"';
    }

    if (const auto trimmed = truncateFeedbackNote (note); ! trimmed.empty())
    {
        json += ",\"note\":\"";
        json += jsonEscape (trimmed);
        json += '"';
    }

    if (dropToReadyMs.has_value() && *dropToReadyMs >= 0)
    {
        json += ",\"drop_to_ready_ms\":";
        json += std::to_string (*dropToReadyMs);
    }

    json += '}';
    return json;
}

} // namespace tonamorph::core
