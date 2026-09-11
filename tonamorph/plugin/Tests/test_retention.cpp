#include "TestFramework.h"

#include "Core/Retention.h"
#include "Core/Strings.h"

#include <string>

using namespace tonamorph::core;

namespace
{
    constexpr std::int64_t day = millisecondsPerDay;
    constexpr std::int64_t firstMorph = 1'700'000'000'000LL;   // any epoch instant
}

TONAMORPH_TEST(npsCardWaitsFourteenDaysAfterTheFirstMorph)
{
    NpsState state;
    TONAMORPH_CHECK(!shouldShowNpsCard(state, firstMorph + 30 * day));   // no first morph yet: never

    state.firstMorphAtMs = firstMorph;
    TONAMORPH_CHECK(!shouldShowNpsCard(state, firstMorph));
    TONAMORPH_CHECK(!shouldShowNpsCard(state, firstMorph + 13 * day));
    TONAMORPH_CHECK(!shouldShowNpsCard(state, firstMorph + 14 * day - 1));
    TONAMORPH_CHECK(shouldShowNpsCard(state, firstMorph + 14 * day));
    TONAMORPH_CHECK(shouldShowNpsCard(state, firstMorph + 90 * day));
    TONAMORPH_CHECK(!shouldShowNpsCard(state, firstMorph - day));         // clock went backwards
}

TONAMORPH_TEST(npsCardNeverReturnsAfterAnAnswerOrTwoDismissals)
{
    NpsState state;
    state.firstMorphAtMs = firstMorph;
    const auto later = firstMorph + 20 * day;

    state.dismissals = 1;
    TONAMORPH_CHECK(shouldShowNpsCard(state, later));    // one "Not now": ask once more
    state.dismissals = 2;
    TONAMORPH_CHECK(!shouldShowNpsCard(state, later));   // twice: never again
    state.dismissals = 5;
    TONAMORPH_CHECK(!shouldShowNpsCard(state, later));

    state.dismissals = 0;
    state.answered = true;
    TONAMORPH_CHECK(!shouldShowNpsCard(state, later));
    TONAMORPH_CHECK_EQ(npsMaxDismissals, 2);
    TONAMORPH_CHECK_EQ(npsDelayDays, 14);
}

TONAMORPH_TEST(npsJsonCarriesScoreAndOptionalComment)
{
    TONAMORPH_CHECK_EQ(buildNpsJson(9, ""), std::string("{\"score\":9}"));
    TONAMORPH_CHECK_EQ(buildNpsJson(9, "   "), std::string("{\"score\":9}"));
    TONAMORPH_CHECK_EQ(buildNpsJson(10, " Fast \"and\" in key "),
                       std::string("{\"score\":10,\"comment\":\"Fast \\\"and\\\" in key\"}"));
    TONAMORPH_CHECK_EQ(buildNpsJson(-3, ""), std::string("{\"score\":0}"));    // clamped
    TONAMORPH_CHECK_EQ(buildNpsJson(42, ""), std::string("{\"score\":10}"));

    const std::string longComment(600, 'x');
    const auto json = buildNpsJson(7, longComment);
    TONAMORPH_CHECK_EQ(json.size(), std::string("{\"score\":7,\"comment\":\"\"}").size() + maxNpsCommentLength);
    TONAMORPH_CHECK_EQ(maxNpsCommentLength, static_cast<std::size_t>(500));

    TONAMORPH_CHECK(isValidNpsScore(0) && isValidNpsScore(10));
    TONAMORPH_CHECK(!isValidNpsScore(-1) && !isValidNpsScore(11));
}

TONAMORPH_TEST(weekOneGiftIsExactlyTwoCreditsOnDaySevenOrEight)
{
    const std::optional<std::int64_t> first = firstMorph;

    TONAMORPH_CHECK(isWeekOneGiftDelta(3, 5, first, firstMorph + 7 * day));
    TONAMORPH_CHECK(isWeekOneGiftDelta(0, 2, first, firstMorph + 7 * day + 12 * 60 * 60 * 1000));
    TONAMORPH_CHECK(isWeekOneGiftDelta(3, 5, first, firstMorph + 8 * day + day - 1));   // late cron: day 8 still counts
    TONAMORPH_CHECK(!isWeekOneGiftDelta(3, 5, first, firstMorph + 9 * day));
    TONAMORPH_CHECK(!isWeekOneGiftDelta(3, 5, first, firstMorph + 6 * day + day - 1));

    TONAMORPH_CHECK(!isWeekOneGiftDelta(3, 4, first, firstMorph + 7 * day));    // a refund
    TONAMORPH_CHECK(!isWeekOneGiftDelta(3, 6, first, firstMorph + 7 * day));    // a referral grant
    TONAMORPH_CHECK(!isWeekOneGiftDelta(3, 53, first, firstMorph + 7 * day));   // a purchase
    TONAMORPH_CHECK(!isWeekOneGiftDelta(5, 3, first, firstMorph + 7 * day));    // a charge
    TONAMORPH_CHECK(!isWeekOneGiftDelta(3, 5, std::nullopt, firstMorph + 7 * day));
    TONAMORPH_CHECK(!isWeekOneGiftDelta(3, 5, first, firstMorph - day));

    TONAMORPH_CHECK_EQ(std::string(weekOneGiftKey), std::string("gift:week1"));
    TONAMORPH_CHECK_EQ(weekOneGiftCredits, 2);
}

TONAMORPH_TEST(referralStringsMatchThePlan)
{
    TONAMORPH_CHECK_EQ(referralPromiseLine(),
                       std::string("They get 5 free morphs. You get 3 when their first morph lands."));
    TONAMORPH_CHECK_EQ(std::string(tonamorph::strings::referralShare), std::string("Send a morph to a friend"));
    TONAMORPH_CHECK_EQ(std::string(tonamorph::strings::giftWeekOne), std::string("One week in. Two morphs on us."));
    TONAMORPH_CHECK_EQ(tonamorph::strings::fill(tonamorph::strings::fill(tonamorph::strings::referralStats, "friends", "2"),
                                                "morphs", "6"),
                       std::string("2 joined · 6 morphs earned"));
    TONAMORPH_CHECK_EQ(tonamorph::strings::fill(tonamorph::strings::npsQuestion, "product", tonamorph::strings::productName),
                       std::string("How likely are you to recommend Tonamorph? 0–10"));
}
