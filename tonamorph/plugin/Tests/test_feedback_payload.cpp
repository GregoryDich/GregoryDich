#include "TestFramework.h"

#include "Core/FeedbackPayload.h"

#include <string>

using namespace tonamorph::core;

TONAMORPH_TEST(feedbackJsonMatchesContractShape)
{
    TONAMORPH_CHECK_EQ(buildFeedbackJson(true, "", "", 1234),
                       std::string(R"({"rating":"up","drop_to_ready_ms":1234})"));

    TONAMORPH_CHECK_EQ(buildFeedbackJson(false, "bleed", "Kick leaks into the bass", 5200),
                       std::string(R"({"rating":"down","reason":"bleed","note":"Kick leaks into the bass","drop_to_ready_ms":5200})"));

    // No timing known, no reason, no note: only the rating is sent.
    TONAMORPH_CHECK_EQ(buildFeedbackJson(false, "", "   ", std::nullopt), std::string(R"({"rating":"down"})"));
    // A negative timing is meaningless and dropped.
    TONAMORPH_CHECK_EQ(buildFeedbackJson(true, "", "", -1), std::string(R"({"rating":"up"})"));
}

TONAMORPH_TEST(feedbackReasonsAreTheContractList)
{
    TONAMORPH_CHECK_EQ(feedbackReasons.size(), static_cast<std::size_t>(6));
    for (const char* reason : { "bleed", "wrong_key", "midi_off", "clicks", "slow", "other" })
        TONAMORPH_CHECK(isValidFeedbackReason(reason));

    TONAMORPH_CHECK(!isValidFeedbackReason("noisy"));
    // An unknown reason is omitted rather than sent and rejected with 422.
    TONAMORPH_CHECK_EQ(buildFeedbackJson(false, "noisy", "", std::nullopt), std::string(R"({"rating":"down"})"));
}

TONAMORPH_TEST(feedbackNoteIsTrimmedTruncatedAndEscaped)
{
    TONAMORPH_CHECK_EQ(truncateFeedbackNote("  hello \n"), std::string("hello"));

    const std::string longNote(200, 'x');
    TONAMORPH_CHECK_EQ(truncateFeedbackNote(longNote).size(), maxFeedbackNoteLength);

    // 139 ASCII characters followed by a two-byte code point: the code point counts as one
    // and fits; a further byte does not.
    std::string mixed(139, 'a');
    mixed += "\xc3\xa9";   // é
    mixed += 'b';
    const auto cut = truncateFeedbackNote(mixed);
    TONAMORPH_CHECK_EQ(cut.size(), static_cast<std::size_t>(141));
    TONAMORPH_CHECK_EQ(cut.substr(139), std::string("\xc3\xa9"));

    TONAMORPH_CHECK_EQ(jsonEscape("say \"hi\"\\\n\t\x01"), std::string("say \\\"hi\\\"\\\\\\n\\t\\u0001"));
    TONAMORPH_CHECK_EQ(buildFeedbackJson(false, "other", "a \"quoted\" note", std::nullopt),
                       std::string(R"({"rating":"down","reason":"other","note":"a \"quoted\" note"})"));
}
