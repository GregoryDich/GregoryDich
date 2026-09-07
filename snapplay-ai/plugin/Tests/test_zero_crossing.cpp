#include "TestFramework.h"

#include "Core/ZeroCrossing.h"

#include <vector>

namespace
{

// Crossings (zero sample or sign change) at indices 0, 5, 8 and 11.
const std::vector<float> wave { 0.0f, 0.5f, 0.9f, 0.5f, 0.1f, -0.3f, -0.8f, -0.3f, 0.2f, 0.7f, 0.2f, -0.4f };

} // namespace

SNAPPLAY_TEST(nearestZeroCrossingSearchesOutward)
{
    using snapplay::core::nearestZeroCrossing;
    const int n = static_cast<int> (wave.size());

    SNAPPLAY_CHECK_EQ (nearestZeroCrossing (wave.data(), n, 2), 0);    // 2 back vs 3 forward
    SNAPPLAY_CHECK_EQ (nearestZeroCrossing (wave.data(), n, 4), 5);    // 4 back vs 1 forward
    SNAPPLAY_CHECK_EQ (nearestZeroCrossing (wave.data(), n, 6), 5);
    SNAPPLAY_CHECK_EQ (nearestZeroCrossing (wave.data(), n, 7), 8);
    SNAPPLAY_CHECK_EQ (nearestZeroCrossing (wave.data(), n, 5), 5);    // already on a crossing
    SNAPPLAY_CHECK_EQ (nearestZeroCrossing (wave.data(), n, 100), 11); // clamped into the buffer
    SNAPPLAY_CHECK_EQ (nearestZeroCrossing (wave.data(), n, -5), 0);
}

SNAPPLAY_TEST(nearestZeroCrossingTiesResolveEarlierAndWindowLimits)
{
    using snapplay::core::nearestZeroCrossing;

    const std::vector<float> tie { 0.5f, -0.5f, -0.5f, 0.5f, 0.5f };   // crossings at 1 and 3
    SNAPPLAY_CHECK_EQ (nearestZeroCrossing (tie.data(), 5, 2), 1);

    const int n = static_cast<int> (wave.size());
    SNAPPLAY_CHECK_EQ (nearestZeroCrossing (wave.data(), n, 2, 1), 2);   // nothing within +-1
    SNAPPLAY_CHECK_EQ (nearestZeroCrossing (wave.data(), n, 2, 2), 0);

    const std::vector<float> positive { 0.3f, 0.4f, 0.5f, 0.4f };
    SNAPPLAY_CHECK_EQ (nearestZeroCrossing (positive.data(), 4, 2), 2);   // no crossing at all

    SNAPPLAY_CHECK_EQ (nearestZeroCrossing (nullptr, 0, 3), 0);
    SNAPPLAY_CHECK_EQ (nearestZeroCrossing (wave.data(), 0, 3), 0);
}

SNAPPLAY_TEST(findTrimRangeSnapsAudibleRegionToCrossings)
{
    using snapplay::core::findTrimRange;

    std::vector<float> buffer (10, 0.0f);
    buffer.insert (buffer.end(), { 0.0005f, 0.0008f });                                           // 10, 11: below -60 dB
    buffer.insert (buffer.end(), { 0.2f, 0.6f, 0.9f, 0.6f, 0.2f, -0.2f, -0.6f, -0.9f, -0.6f, -0.2f }); // 12..21 audible
    buffer.insert (buffer.end(), { 0.0005f, 0.0002f });                                           // 22, 23: tail
    buffer.insert (buffer.end(), 10, 0.0f);
    const int n = static_cast<int> (buffer.size());

    const auto range = findTrimRange (buffer.data(), n);
    SNAPPLAY_CHECK_EQ (range.start, 9);    // first audible is 12, moved back to the zero at 9
    SNAPPLAY_CHECK_EQ (range.end, 22);     // last audible is 21, sign flips at 22
    SNAPPLAY_CHECK_EQ (range.length(), 13);

    const auto loud = findTrimRange (buffer.data(), n, 0.5f);
    SNAPPLAY_CHECK_EQ (loud.start, 9);
    SNAPPLAY_CHECK_EQ (loud.end, 22);

    const auto narrow = findTrimRange (buffer.data(), n, 0.001f, 1);   // no crossing within one sample of 12
    SNAPPLAY_CHECK_EQ (narrow.start, 12);
    SNAPPLAY_CHECK_EQ (narrow.end, 22);
}

SNAPPLAY_TEST(findTrimRangeDegenerateInputs)
{
    using snapplay::core::findTrimRange;

    const std::vector<float> silence (50, 0.0f);
    const auto whole = findTrimRange (silence.data(), 50);
    SNAPPLAY_CHECK_EQ (whole.start, 0);
    SNAPPLAY_CHECK_EQ (whole.end, 50);

    const auto empty = findTrimRange (nullptr, 0);
    SNAPPLAY_CHECK_EQ (empty.start, 0);
    SNAPPLAY_CHECK_EQ (empty.end, 0);

    const std::vector<float> loudToTheEnd { 0.0f, 0.0f, 0.5f, 0.7f, 0.6f };
    const auto range = findTrimRange (loudToTheEnd.data(), 5);
    SNAPPLAY_CHECK_EQ (range.start, 1);
    SNAPPLAY_CHECK_EQ (range.end, 5);
}
