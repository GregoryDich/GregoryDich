#pragma once

/**
 * Minimal self-contained assertion framework for the JUCE-free core tests.
 *
 * Usage:
 * @code
 *   TONAMORPH_TEST(scaleLockSnapsDownOnTies)
 *   {
 *       tonamorph::core::ScaleLock lock;
 *       lock.setScale({ 0, 2 });
 *       TONAMORPH_CHECK_EQ(lock.snap(1), 0);
 *   }
 * @endcode
 *
 * Every TONAMORPH_TEST registers itself at static-initialisation time; main()
 * runs all registered tests and returns a non-zero exit code on any failure.
 */

#include <cmath>
#include <functional>
#include <sstream>
#include <string>
#include <vector>

namespace tonamorph::test
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

} // namespace tonamorph::test

#define TONAMORPH_TEST(name)                                                              \
    static void tonamorphTest_##name();                                                   \
    static const tonamorph::test::Registrar tonamorphRegistrar_##name (#name, &tonamorphTest_##name); \
    static void tonamorphTest_##name()

#define TONAMORPH_CHECK(condition)                                                        \
    do {                                                                                 \
        if (! (condition))                                                               \
            tonamorph::test::reportFailure (__FILE__, __LINE__, "check failed: " #condition); \
    } while (false)

#define TONAMORPH_CHECK_EQ(actual, expected)                                              \
    do {                                                                                 \
        const auto tonamorphActual = (actual);                                            \
        const auto tonamorphExpected = (expected);                                        \
        if (! (tonamorphActual == tonamorphExpected))                                      \
        {                                                                                \
            std::ostringstream tonamorphStream;                                           \
            tonamorphStream << "expected " #actual " == " #expected " (got "              \
                           << tonamorphActual << ", expected " << tonamorphExpected << ")"; \
            tonamorph::test::reportFailure (__FILE__, __LINE__, tonamorphStream.str());    \
        }                                                                                \
    } while (false)

#define TONAMORPH_CHECK_NEAR(actual, expected, tolerance)                                 \
    do {                                                                                 \
        const double tonamorphActual = static_cast<double> (actual);                      \
        const double tonamorphExpected = static_cast<double> (expected);                  \
        if (std::fabs (tonamorphActual - tonamorphExpected) > static_cast<double> (tolerance)) \
        {                                                                                \
            std::ostringstream tonamorphStream;                                           \
            tonamorphStream << "expected " #actual " ~= " #expected " (got "              \
                           << tonamorphActual << ", expected " << tonamorphExpected        \
                           << " +/- " << (tolerance) << ")";                             \
            tonamorph::test::reportFailure (__FILE__, __LINE__, tonamorphStream.str());    \
        }                                                                                \
    } while (false)
