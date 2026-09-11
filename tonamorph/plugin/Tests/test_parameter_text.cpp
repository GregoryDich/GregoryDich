#include "TestFramework.h"

#include "Core/ParameterText.h"

#include <string>

using namespace tonamorph::core;

namespace
{
    constexpr double silenceDb = -60.0;
}

TONAMORPH_TEST(millisecondsFormatWithUnitAndSensiblePrecision)
{
    TONAMORPH_CHECK_EQ(formatMilliseconds(2.0), std::string("2.0 ms"));
    TONAMORPH_CHECK_EQ(formatMilliseconds(3.9999971), std::string("4.0 ms"));   // the knob bug: never a raw float
    TONAMORPH_CHECK_EQ(formatMilliseconds(120.0), std::string("120 ms"));
    TONAMORPH_CHECK_EQ(formatMilliseconds(999.4), std::string("999 ms"));
    TONAMORPH_CHECK_EQ(formatMilliseconds(1200.0), std::string("1.20 s"));
    TONAMORPH_CHECK_EQ(formatMilliseconds(5000.0), std::string("5.00 s"));

    TONAMORPH_CHECK_NEAR(parseMilliseconds("120 ms").value_or(-1.0), 120.0, 1e-9);
    TONAMORPH_CHECK_NEAR(parseMilliseconds("120").value_or(-1.0), 120.0, 1e-9);
    TONAMORPH_CHECK_NEAR(parseMilliseconds(" 1.2 s ").value_or(-1.0), 1200.0, 1e-9);
    TONAMORPH_CHECK_NEAR(parseMilliseconds("1.2S").value_or(-1.0), 1200.0, 1e-9);
    TONAMORPH_CHECK(!parseMilliseconds("fast").has_value());
    TONAMORPH_CHECK(!parseMilliseconds("120 Hz").has_value());
    TONAMORPH_CHECK(!parseMilliseconds("").has_value());
}

TONAMORPH_TEST(percentFormatsAFractionAndReadsBothSpellings)
{
    TONAMORPH_CHECK_EQ(formatPercent(0.8), std::string("80 %"));
    TONAMORPH_CHECK_EQ(formatPercent(0.0), std::string("0 %"));
    TONAMORPH_CHECK_EQ(formatPercent(1.0), std::string("100 %"));
    TONAMORPH_CHECK_EQ(formatPercent(0.004), std::string("0 %"));   // no "-0"

    TONAMORPH_CHECK_NEAR(parsePercent("80 %").value_or(-1.0), 0.8, 1e-9);
    TONAMORPH_CHECK_NEAR(parsePercent("80%").value_or(-1.0), 0.8, 1e-9);
    TONAMORPH_CHECK_NEAR(parsePercent("80").value_or(-1.0), 0.8, 1e-9);
    TONAMORPH_CHECK_NEAR(parsePercent("0.5").value_or(-1.0), 0.5, 1e-9);
    TONAMORPH_CHECK_NEAR(parsePercent("1").value_or(-1.0), 1.0, 1e-9);
    TONAMORPH_CHECK(!parsePercent("half").has_value());
}

TONAMORPH_TEST(decibelsShowOneDecimalAndInfinityAtTheFloor)
{
    TONAMORPH_CHECK_EQ(formatDecibels(0.0, silenceDb), std::string("0.0 dB"));
    TONAMORPH_CHECK_EQ(formatDecibels(-0.04, silenceDb), std::string("0.0 dB"));
    TONAMORPH_CHECK_EQ(formatDecibels(-6.02, silenceDb), std::string("-6.0 dB"));
    TONAMORPH_CHECK_EQ(formatDecibels(12.0, silenceDb), std::string("12.0 dB"));
    TONAMORPH_CHECK_EQ(formatDecibels(-60.0, silenceDb), std::string("-inf dB"));
    TONAMORPH_CHECK_EQ(formatDecibels(-59.9, silenceDb), std::string("-59.9 dB"));

    TONAMORPH_CHECK_NEAR(parseDecibels("-6 dB", silenceDb).value_or(1.0), -6.0, 1e-9);
    TONAMORPH_CHECK_NEAR(parseDecibels("-6", silenceDb).value_or(1.0), -6.0, 1e-9);
    TONAMORPH_CHECK_NEAR(parseDecibels("-inf dB", silenceDb).value_or(1.0), silenceDb, 1e-9);
    TONAMORPH_CHECK_NEAR(parseDecibels("-INF", silenceDb).value_or(1.0), silenceDb, 1e-9);
    TONAMORPH_CHECK(!parseDecibels("loud", silenceDb).has_value());
    TONAMORPH_CHECK(!parseDecibels("6 Hz", silenceDb).has_value());
}

TONAMORPH_TEST(hertzSwitchToKilohertzAboveAThousand)
{
    TONAMORPH_CHECK_EQ(formatHertz(20.0), std::string("20 Hz"));
    TONAMORPH_CHECK_EQ(formatHertz(250.4), std::string("250 Hz"));
    TONAMORPH_CHECK_EQ(formatHertz(999.4), std::string("999 Hz"));
    TONAMORPH_CHECK_EQ(formatHertz(1000.0), std::string("1.00 kHz"));
    TONAMORPH_CHECK_EQ(formatHertz(1250.0), std::string("1.25 kHz"));
    TONAMORPH_CHECK_EQ(formatHertz(12500.0), std::string("12.5 kHz"));
    TONAMORPH_CHECK_EQ(formatHertz(20000.0), std::string("20.0 kHz"));

    TONAMORPH_CHECK_NEAR(parseHertz("250 Hz").value_or(-1.0), 250.0, 1e-9);
    TONAMORPH_CHECK_NEAR(parseHertz("250").value_or(-1.0), 250.0, 1e-9);
    TONAMORPH_CHECK_NEAR(parseHertz("1.25 kHz").value_or(-1.0), 1250.0, 1e-9);
    TONAMORPH_CHECK_NEAR(parseHertz("2k").value_or(-1.0), 2000.0, 1e-9);
    TONAMORPH_CHECK_NEAR(parseHertz("20KHZ").value_or(-1.0), 20000.0, 1e-9);
    TONAMORPH_CHECK(!parseHertz("bright").has_value());
    TONAMORPH_CHECK(!parseHertz("2 ms").has_value());
}

TONAMORPH_TEST(ratioHasTwoDecimalsAndNoUnit)
{
    TONAMORPH_CHECK_EQ(formatRatio(0.7071), std::string("0.71"));
    TONAMORPH_CHECK_EQ(formatRatio(10.0), std::string("10.00"));
    TONAMORPH_CHECK_NEAR(parseRatio(" 0.71 ").value_or(-1.0), 0.71, 1e-9);
    TONAMORPH_CHECK(!parseRatio("0.71 Q").has_value());
    TONAMORPH_CHECK(!parseRatio("x").has_value());
}

TONAMORPH_TEST(noteNamesUseMiddleCFourAndRoundTrip)
{
    TONAMORPH_CHECK_EQ(formatNoteName(60), std::string("C4"));
    TONAMORPH_CHECK_EQ(formatNoteName(48), std::string("C3"));    // the contract's default root target
    TONAMORPH_CHECK_EQ(formatNoteName(24), std::string("C1"));
    TONAMORPH_CHECK_EQ(formatNoteName(84), std::string("C6"));
    TONAMORPH_CHECK_EQ(formatNoteName(70), std::string("A#4"));
    TONAMORPH_CHECK_EQ(formatNoteName(0), std::string("C-1"));
    TONAMORPH_CHECK_EQ(formatNoteName(200), std::string("G9"));   // clamped to 127

    for (int note = 24; note <= 84; ++note)
        TONAMORPH_CHECK_EQ(parseNoteName(formatNoteName(note)).value_or(-1), note);

    TONAMORPH_CHECK_EQ(parseNoteName("f#2").value_or(-1), 42);
    TONAMORPH_CHECK_EQ(parseNoteName("Bb1").value_or(-1), 34);
    TONAMORPH_CHECK_EQ(parseNoteName(" A 4 ").value_or(-1), 69);
    TONAMORPH_CHECK_EQ(parseNoteName("48").value_or(-1), 48);
    TONAMORPH_CHECK(!parseNoteName("C").has_value());
    TONAMORPH_CHECK(!parseNoteName("H3").has_value());
    TONAMORPH_CHECK(!parseNoteName("").has_value());

    TONAMORPH_CHECK_EQ(formatPitchClassName(0), std::string("C"));
    TONAMORPH_CHECK_EQ(formatPitchClassName(6), std::string("F#"));
    TONAMORPH_CHECK_EQ(formatPitchClassName(-1), std::string("B"));
    TONAMORPH_CHECK_EQ(formatPitchClassName(13), std::string("C#"));

    for (int pitchClass = 0; pitchClass < 12; ++pitchClass)
        TONAMORPH_CHECK_EQ(parsePitchClassName(formatPitchClassName(pitchClass)).value_or(-1), pitchClass);

    TONAMORPH_CHECK_EQ(parsePitchClassName("Bb").value_or(-1), 10);
    TONAMORPH_CHECK_EQ(parsePitchClassName("3").value_or(-1), 3);
    TONAMORPH_CHECK(!parsePitchClassName("X").has_value());
}
