#include "TestFramework.h"

#include "Core/Types.h"
#include "Core/ScaleLock.h"

// Smoke test proving the framework runs and the Core headers compile without JUCE.
TONAMORPH_TEST(coreHeadersCompileAndScaleLockPassesThroughWhenEmpty)
{
    tonamorph::core::ScaleLock lock;
    TONAMORPH_CHECK(lock.isPassthrough());
    TONAMORPH_CHECK_EQ(lock.snap(61), 61);
}
