#include "TestFramework.h"

#include "Core/ScaleLock.h"

#include <vector>

// Contract §8 table: intervals for the computed modes, rotated to the root.
TONAMORPH_TEST(pitchClassesForComputesContractTable)
{
    using tonamorph::core::ScaleMode;
    using tonamorph::core::pitchClassesFor;

    TONAMORPH_CHECK(pitchClassesFor(ScaleMode::Major, 0) == (std::vector<int>{ 0, 2, 4, 5, 7, 9, 11 }));
    TONAMORPH_CHECK(pitchClassesFor(ScaleMode::Minor, 0) == (std::vector<int>{ 0, 2, 3, 5, 7, 8, 10 }));
    TONAMORPH_CHECK(pitchClassesFor(ScaleMode::PentatonicMajor, 0) == (std::vector<int>{ 0, 2, 4, 7, 9 }));
    TONAMORPH_CHECK(pitchClassesFor(ScaleMode::PentatonicMinor, 0) == (std::vector<int>{ 0, 3, 5, 7, 10 }));
    // F minor (root 5): 5 7 8 10 0 1 3 sorted ascending.
    TONAMORPH_CHECK(pitchClassesFor(ScaleMode::Minor, 5) == (std::vector<int>{ 0, 1, 3, 5, 7, 8, 10 }));
    TONAMORPH_CHECK(pitchClassesFor(ScaleMode::Detected, 5).empty());
    TONAMORPH_CHECK(pitchClassesFor(ScaleMode::Off, 5).empty());
}

TONAMORPH_TEST(snapResolvesTiesDownward)
{
    tonamorph::core::ScaleLock lock;
    lock.setMode(tonamorph::core::ScaleMode::Major, 0);   // C major

    TONAMORPH_CHECK(!lock.isPassthrough());
    TONAMORPH_CHECK_EQ(lock.snap(60), 60);   // C stays
    TONAMORPH_CHECK_EQ(lock.snap(61), 60);   // C# between C and D: tie -> down
    TONAMORPH_CHECK_EQ(lock.snap(63), 62);   // D# tie between D and E -> down
    TONAMORPH_CHECK_EQ(lock.snap(66), 65);   // F# tie between F and G -> down
    TONAMORPH_CHECK_EQ(lock.snap(0), 0);
    TONAMORPH_CHECK_EQ(lock.snap(127), 127); // G is in C major
}

TONAMORPH_TEST(detectedModeUsesInstalledScaleVerbatim)
{
    tonamorph::core::ScaleLock lock;
    lock.setMode(tonamorph::core::ScaleMode::Detected, 9);   // root ignored for Detected
    TONAMORPH_CHECK(lock.isPassthrough());

    lock.setScale({ 5, 7, 8, 10, 0, 1, 3 });   // F minor from the contract example
    TONAMORPH_CHECK(!lock.isPassthrough());
    TONAMORPH_CHECK_EQ(lock.snap(64), 63);   // E -> Eb (tie between Eb and F resolves down)
    TONAMORPH_CHECK_EQ(lock.snap(65), 65);

    lock.setMode(tonamorph::core::ScaleMode::Off, 0);
    TONAMORPH_CHECK(lock.isPassthrough());
    TONAMORPH_CHECK_EQ(lock.snap(64), 64);
}

TONAMORPH_TEST(maskHelpersMatchTheModel)
{
    using namespace tonamorph::core;

    const auto mask = pitchClassMask({ 0, 4, 7 });
    TONAMORPH_CHECK_EQ(static_cast<int>(mask), (1 << 0) | (1 << 4) | (1 << 7));
    TONAMORPH_CHECK_EQ(snapToMask(62, mask), 60);   // D: C at 2 below, E at 2 above -> down
    TONAMORPH_CHECK_EQ(snapToMask(66, mask), 67);   // F#: E at 2 below, G at 1 above -> nearest
    TONAMORPH_CHECK_EQ(snapToMask(50, 0), 50);      // empty mask passes through
}
