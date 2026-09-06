#include "TestFramework.h"

#include "Core/Types.h"
#include "Core/ScaleLock.h"

// Smoke test proving the framework runs and the Core headers compile without JUCE.
SNAPPLAY_TEST(coreHeadersCompileAndScaleLockPassesThroughWhenEmpty)
{
    snapplay::core::ScaleLock lock;
    SNAPPLAY_CHECK(lock.isPassthrough());
    SNAPPLAY_CHECK_EQ(lock.snap(61), 61);
}
