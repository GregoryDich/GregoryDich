#pragma once

/**
 * Retry schedule for the API client: exponential backoff with jitter on 429 / 502 / 503 /
 * 504 and transport errors, honouring `Retry-After` (contract §5). Standard-library only
 * so the schedule can be unit-tested without JUCE.
 */

#include <algorithm>
#include <string_view>

namespace snapplay::cloud::retry
{

inline constexpr int maxBackoffMs = 8000;
inline constexpr int maxRetryAfterMs = 60000;
inline constexpr double jitterFraction = 0.25;

/** Statuses that are worth retrying: rate limited or a transient upstream failure. */
inline bool isRetryableStatus (int status) noexcept
{
    return status == 429 || status == 502 || status == 503 || status == 504;
}

/**
 * Delay before retry number `attempt` (0 = first retry).
 * @param initialBackoffMs  base delay, doubled per attempt and capped at maxBackoffMs
 * @param jitterUnit        random value in [0, 1); adds up to 25 % of the base delay
 * @param retryAfterMs      value of a `Retry-After` header, or a negative number when absent;
 *                          when present it replaces the computed delay (capped at 60 s)
 */
inline int backoffDelayMs (int attempt, int initialBackoffMs, double jitterUnit, int retryAfterMs = -1) noexcept
{
    if (retryAfterMs >= 0)
        return std::min (retryAfterMs, maxRetryAfterMs);

    const long long base = std::max (0, initialBackoffMs);
    const int shift = std::clamp (attempt, 0, 20);
    const long long scaled = std::min<long long> (base << shift, maxBackoffMs);
    const double jitter = std::clamp (jitterUnit, 0.0, 1.0) * jitterFraction * static_cast<double> (scaled);

    return static_cast<int> (scaled) + static_cast<int> (jitter);
}

/** Parses a `Retry-After` value given in seconds; returns -1 for absent, HTTP-date or
    malformed values (the caller then falls back to the computed backoff). */
inline int parseRetryAfterMs (std::string_view value) noexcept
{
    while (! value.empty() && (value.front() == ' ' || value.front() == '\t'))
        value.remove_prefix (1);

    while (! value.empty() && (value.back() == ' ' || value.back() == '\t' || value.back() == '\r' || value.back() == '\n'))
        value.remove_suffix (1);

    if (value.empty() || value.size() > 9)
        return -1;

    long long seconds = 0;

    for (const char c : value)
    {
        if (c < '0' || c > '9')
            return -1;

        seconds = seconds * 10 + (c - '0');
    }

    return static_cast<int> (std::min<long long> (seconds * 1000, maxRetryAfterMs));
}

} // namespace snapplay::cloud::retry
