#include "TestFramework.h"

#include "Core/ScaleLock.h"

#include <vector>

// Contract §8 table: intervals for the computed modes, rotated to the root.
SNAPPLAY_TEST(pitchClassesForComputesContractTable)
{
    using snapplay::core::ScaleMode;
    using snapplay::core::pitchClassesFor;

    SNAPPLAY_CHECK(pitchClassesFor(ScaleMode::Major, 0) == (std::vector<int>{ 0, 2, 4, 5, 7, 9, 11 }));
    SNAPPLAY_CHECK(pitchClassesFor(ScaleMode::Minor, 0) == (std::vector<int>{ 0, 2, 3, 5, 7, 8, 10 }));
    SNAPPLAY_CHECK(pitchClassesFor(ScaleMode::PentatonicMajor, 0) == (std::vector<int>{ 0, 2, 4, 7, 9 }));
    SNAPPLAY_CHECK(pitchClassesFor(ScaleMode::PentatonicMinor, 0) == (std::vector<int>{ 0, 3, 5, 7, 10 }));
    // F minor (root 5): 5 7 8 10 0 1 3 sorted ascending.
    SNAPPLAY_CHECK(pitchClassesFor(ScaleMode::Minor, 5) == (std::vector<int>{ 0, 1, 3, 5, 7, 8, 10 }));
    SNAPPLAY_CHECK(pitchClassesFor(ScaleMode::Detected, 5).empty());
    SNAPPLAY_CHECK(pitchClassesFor(ScaleMode::Off, 5).empty());
}

SNAPPLAY_TEST(snapResolvesTiesDownward)
{
    snapplay::core::ScaleLock lock;
    lock.setMode(snapplay::core::ScaleMode::Major, 0);   // C major

    SNAPPLAY_CHECK(!lock.isPassthrough());
    SNAPPLAY_CHECK_EQ(lock.snap(60), 60);   // C stays
    SNAPPLAY_CHECK_EQ(lock.snap(61), 60);   // C# between C and D: tie -> down
    SNAPPLAY_CHECK_EQ(lock.snap(63), 62);   // D# tie between D and E -> down
    SNAPPLAY_CHECK_EQ(lock.snap(66), 65);   // F# tie between F and G -> down
    SNAPPLAY_CHECK_EQ(lock.snap(0), 0);
    SNAPPLAY_CHECK_EQ(lock.snap(127), 127); // G is in C major
}

SNAPPLAY_TEST(detectedModeUsesInstalledScaleVerbatim)
{
    snapplay::core::ScaleLock lock;
    lock.setMode(snapplay::core::ScaleMode::Detected, 9);   // root ignored for Detected
    SNAPPLAY_CHECK(lock.isPassthrough());

    lock.setScale({ 5, 7, 8, 10, 0, 1, 3 });   // F minor from the contract example
    SNAPPLAY_CHECK(!lock.isPassthrough());
    SNAPPLAY_CHECK_EQ(lock.snap(64), 63);   // E -> Eb (tie between Eb and F resolves down)
    SNAPPLAY_CHECK_EQ(lock.snap(65), 65);

    lock.setMode(snapplay::core::ScaleMode::Off, 0);
    SNAPPLAY_CHECK(lock.isPassthrough());
    SNAPPLAY_CHECK_EQ(lock.snap(64), 64);
}

SNAPPLAY_TEST(maskHelpersMatchTheModel)
{
    using namespace snapplay::core;

    const auto mask = pitchClassMask({ 0, 4, 7 });
    SNAPPLAY_CHECK_EQ(static_cast<int>(mask), (1 << 0) | (1 << 4) | (1 << 7));
    SNAPPLAY_CHECK_EQ(snapToMask(62, mask), 60);   // D: C at 2 below, E at 2 above -> down
    SNAPPLAY_CHECK_EQ(snapToMask(66, mask), 67);   // F#: E at 2 below, G at 1 above -> nearest
    SNAPPLAY_CHECK_EQ(snapToMask(50, 0), 50);      // empty mask passes through
}
