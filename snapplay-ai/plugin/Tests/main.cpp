#include "TestFramework.h"

#include <cstdio>
#include <exception>

namespace snapplay::test
{

void reportFailure (const char* file, int line, const std::string& message)
{
    ++currentFailures();
    std::printf ("    FAIL %s:%d: %s\n", file, line, message.c_str());
}

} // namespace snapplay::test

int main()
{
    using namespace snapplay::test;

    int passed = 0;
    int failed = 0;

    for (const auto& testCase : registry())
    {
        currentFailures() = 0;
        std::printf ("[ RUN  ] %s\n", testCase.name.c_str());

        try
        {
            testCase.body();
        }
        catch (const std::exception& e)
        {
            reportFailure ("<exception>", 0, e.what());
        }
        catch (...)
        {
            reportFailure ("<exception>", 0, "unknown exception");
        }

        if (currentFailures() == 0)
        {
            ++passed;
            std::printf ("[  OK  ] %s\n", testCase.name.c_str());
        }
        else
        {
            ++failed;
            std::printf ("[ FAIL ] %s (%d failed checks)\n", testCase.name.c_str(), currentFailures());
        }
    }

    std::printf ("\n%d passed, %d failed, %d total\n", passed, failed, passed + failed);
    return failed == 0 ? 0 : 1;
}
