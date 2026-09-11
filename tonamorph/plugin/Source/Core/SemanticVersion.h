#pragma once

/**
 * Semantic version parsing and ordering for the `GET /v1/version` banner. Accepts
 * "1.2.3", "v1.2.3", "1.2" (patch 0) and a "-prerelease" suffix; a release orders after
 * its pre-releases. Standard-library only so the comparison is unit-tested without JUCE.
 */

#include <cctype>
#include <optional>
#include <string>
#include <string_view>

namespace tonamorph::core
{

struct SemanticVersion
{
    int major = 0;
    int minor = 0;
    int patch = 0;
    std::string prerelease;   ///< text after the first '-', empty for a release

    bool isRelease() const noexcept { return prerelease.empty(); }
};

/** nullopt for anything that is not `[v]N[.N[.N]][-suffix]`. */
inline std::optional<SemanticVersion> parseSemanticVersion (std::string_view text)
{
    while (! text.empty() && std::isspace (static_cast<unsigned char> (text.front())))
        text.remove_prefix (1);

    while (! text.empty() && std::isspace (static_cast<unsigned char> (text.back())))
        text.remove_suffix (1);

    if (! text.empty() && (text.front() == 'v' || text.front() == 'V'))
        text.remove_prefix (1);

    if (text.empty())
        return std::nullopt;

    SemanticVersion version;

    if (const auto dash = text.find ('-'); dash != std::string_view::npos)
    {
        version.prerelease = std::string (text.substr (dash + 1));
        text = text.substr (0, dash);

        if (version.prerelease.empty())
            return std::nullopt;
    }

    int* fields[] = { &version.major, &version.minor, &version.patch };
    std::size_t fieldIndex = 0;
    std::size_t pos = 0;

    while (pos <= text.size())
    {
        if (fieldIndex >= 3)
            return std::nullopt;

        std::size_t end = pos;
        long long value = 0;

        while (end < text.size() && std::isdigit (static_cast<unsigned char> (text[end])))
        {
            value = value * 10 + (text[end] - '0');

            if (value > 1'000'000)
                return std::nullopt;

            ++end;
        }

        if (end == pos)
            return std::nullopt;   // empty component

        *fields[fieldIndex++] = static_cast<int> (value);

        if (end == text.size())
            break;

        if (text[end] != '.')
            return std::nullopt;

        pos = end + 1;
    }

    return version;
}

/** Negative when `a` orders before `b`, zero when equal, positive otherwise. */
inline int compareVersions (const SemanticVersion& a, const SemanticVersion& b) noexcept
{
    if (a.major != b.major) return a.major < b.major ? -1 : 1;
    if (a.minor != b.minor) return a.minor < b.minor ? -1 : 1;
    if (a.patch != b.patch) return a.patch < b.patch ? -1 : 1;

    if (a.isRelease() != b.isRelease())
        return a.isRelease() ? 1 : -1;

    if (a.prerelease == b.prerelease)
        return 0;

    return a.prerelease < b.prerelease ? -1 : 1;
}

/** True when both parse and `latest` orders after `current`. */
inline bool isNewerVersion (std::string_view latest, std::string_view current)
{
    const auto a = parseSemanticVersion (latest);
    const auto b = parseSemanticVersion (current);
    return a.has_value() && b.has_value() && compareVersions (*a, *b) > 0;
}

/** True when both parse and `current` orders before `minimumSupported`. */
inline bool isBelowMinimumVersion (std::string_view current, std::string_view minimumSupported)
{
    const auto a = parseSemanticVersion (current);
    const auto b = parseSemanticVersion (minimumSupported);
    return a.has_value() && b.has_value() && compareVersions (*a, *b) < 0;
}

} // namespace tonamorph::core
