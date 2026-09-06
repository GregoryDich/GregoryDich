#pragma once

/**
 * Minimal self-contained assertion framework for the JUCE-free core tests.
 *
 * Usage:
 * @code
 *   SNAPPLAY_TEST(scaleLockSnapsDownOnTies)
 *   {
 *       snapplay::core::ScaleLock lock;
 *       lock.setScale({ 0, 2 });
 *       SNAPPLAY_CHECK_EQ(lock.snap(1), 0);
 *   }
 * @endcode
 *
 * Every SNAPPLAY_TEST registers itself at static-initialisation time; main()
 * runs all registered tests and returns a non-zero exit code on any failure.
 */

#include <cmath>
#include <functional>
#include <sstream>
#include <string>
#include <vector>

namespace snapplay::test
{

/** A single registered test case. */
struct TestCase
{
    std::string name;
    std::function<void()> body;
};

/** Global registry of test cases (function-local static to avoid init-order issues). */
inline std::vector<TestCase>& registry()
{
    static std::vector<TestCase> cases;
    return cases;
}

/** Failure counter for the currently running test. */
inline int& currentFailures()
{
    static int failures = 0;
    return failures;
}

/** Registers a test at static-initialisation time. */
struct Registrar
{
    Registrar (const char* name, std::function<void()> body)
    {
        registry().push_back ({ name, std::move (body) });
    }
};

/** Records a failed check with its location and message. */
void reportFailure (const char* file, int line, const std::string& message);

} // namespace snapplay::test

#define SNAPPLAY_TEST(name)                                                              \
    static void snapplayTest_##name();                                                   \
    static const snapplay::test::Registrar snapplayRegistrar_##name (#name, &snapplayTest_##name); \
    static void snapplayTest_##name()

#define SNAPPLAY_CHECK(condition)                                                        \
    do {                                                                                 \
        if (! (condition))                                                               \
            snapplay::test::reportFailure (__FILE__, __LINE__, "check failed: " #condition); \
    } while (false)

#define SNAPPLAY_CHECK_EQ(actual, expected)                                              \
    do {                                                                                 \
        const auto snapplayActual = (actual);                                            \
        const auto snapplayExpected = (expected);                                        \
        if (! (snapplayActual == snapplayExpected))                                      \
        {                                                                                \
            std::ostringstream snapplayStream;                                           \
            snapplayStream << "expected " #actual " == " #expected " (got "              \
                           << snapplayActual << ", expected " << snapplayExpected << ")"; \
            snapplay::test::reportFailure (__FILE__, __LINE__, snapplayStream.str());    \
        }                                                                                \
    } while (false)

#define SNAPPLAY_CHECK_NEAR(actual, expected, tolerance)                                 \
    do {                                                                                 \
        const double snapplayActual = static_cast<double> (actual);                      \
        const double snapplayExpected = static_cast<double> (expected);                  \
        if (std::fabs (snapplayActual - snapplayExpected) > static_cast<double> (tolerance)) \
        {                                                                                \
            std::ostringstream snapplayStream;                                           \
            snapplayStream << "expected " #actual " ~= " #expected " (got "              \
                           << snapplayActual << ", expected " << snapplayExpected        \
                           << " +/- " << (tolerance) << ")";                             \
            snapplay::test::reportFailure (__FILE__, __LINE__, snapplayStream.str());    \
        }                                                                                \
    } while (false)
