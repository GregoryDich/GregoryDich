#pragma once

/**
 * The retention mechanics of GTM §2.4 / Appendix B §3, §5 that have a rule worth testing:
 * the day-14 NPS card (when to show it, the `POST /v1/nps` body), the week-one gift
 * toast (inferred from the balance, see isWeekOneGiftDelta) and the referral promise
 * line. Standard-library only; times are milliseconds since the epoch.
 */

#include <cstdint>
#include <optional>
#include <string>
#include <string_view>

#include "Core/FeedbackPayload.h"   // jsonEscape, trimAndTruncate
#include "Core/Strings.h"

namespace tonamorph::core
{

inline constexpr std::int64_t millisecondsPerDay = 24LL * 60 * 60 * 1000;

//==============================================================================
// NPS card: 14 days after the first own-clip morph, at most twice, never after an answer.

inline constexpr int npsDelayDays = 14;
inline constexpr int npsMaxDismissals = 2;
inline constexpr std::size_t maxNpsCommentLength = 500;   ///< contract §14, in code points

struct NpsState
{
    std::optional<std::int64_t> firstMorphAtMs;   ///< nullopt until the first own-clip morph
    bool answered = false;                        ///< sent (2xx), or refused with 409
    int dismissals = 0;                           ///< "Not now" presses so far
};

inline bool shouldShowNpsCard (const NpsState& state, std::int64_t nowMs) noexcept
{
    if (! state.firstMorphAtMs.has_value() || state.answered || state.dismissals >= npsMaxDismissals)
        return false;

    return nowMs - *state.firstMorphAtMs >= npsDelayDays * millisecondsPerDay;
}

inline bool isValidNpsScore (int score) noexcept
{
    return score >= 0 && score <= 10;
}

/** `{ "score": 9, "comment": "…" }`; the comment is omitted when blank and cut to
    maxNpsCommentLength code points. The score is clamped to 0..10. */
inline std::string buildNpsJson (int score, std::string_view comment)
{
    const int clamped = score < 0 ? 0 : (score > 10 ? 10 : score);
    std::string json = "{\"score\":" + std::to_string (clamped);

    if (const auto trimmed = trimAndTruncate (comment, maxNpsCommentLength); ! trimmed.empty())
    {
        json += ",\"comment\":\"";
        json += jsonEscape (trimmed);
        json += '"';
    }

    json += '}';
    return json;
}

//==============================================================================
// Week-one gift: +2 morphs on day 7 for accounts with at least one morph.

inline constexpr const char* weekOneGiftKey = "gift:week1";   ///< the ledger idempotency key
inline constexpr int weekOneGiftCredits = 2;
inline constexpr int weekOneGiftDay = 7;
inline constexpr int weekOneGiftWindowDays = 2;   ///< day 7 and day 8 (the cron may run late)

/**
 * The `gift:week1` ledger entry is not visible through `GET /v1/me`, so the toast is
 * inferred from the balance poll: `credits` (not `available`, which also moves with
 * reservations) rose by exactly weekOneGiftCredits between two consecutive answers, and
 * the first own-clip morph was 7–8 days ago. Nothing else adds exactly 2 in that window:
 * a purchase adds 50 or 60, a referral grant 3, a refund 1. A -1 charge landing in the
 * same poll interval hides the gift, which is the accepted miss. The editor routes the
 * decision through one function so a server-side `gifts` list replaces this heuristic.
 */
inline bool isWeekOneGiftDelta (int previousCredits, int newCredits,
                                std::optional<std::int64_t> firstMorphAtMs, std::int64_t nowMs) noexcept
{
    if (! firstMorphAtMs.has_value() || newCredits - previousCredits != weekOneGiftCredits)
        return false;

    const auto elapsed = nowMs - *firstMorphAtMs;

    if (elapsed < 0)
        return false;

    const auto days = elapsed / millisecondsPerDay;
    return days >= weekOneGiftDay && days < weekOneGiftDay + weekOneGiftWindowDays;
}

//==============================================================================
// Referral share

/** "They get 5 free morphs. You get 3 when their first morph lands." — kept as two
    entries in the strings table so each respects the twelve-word rule. */
inline std::string referralPromiseLine()
{
    return std::string (strings::referralFriendLine) + " " + strings::referralSenderLine;
}

} // namespace tonamorph::core
