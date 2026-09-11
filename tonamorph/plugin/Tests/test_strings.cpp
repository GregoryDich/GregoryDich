#include "TestFramework.h"

#include "Core/Strings.h"

#include <filesystem>
#include <fstream>
#include <set>
#include <sstream>
#include <string>

using namespace tonamorph::strings;

TONAMORPH_TEST(everyStringIsAtMostTwelveWords)
{
    std::set<std::string> ids;

    for (const auto& entry : table)
    {
        const std::string text(entry.text);
        const int words = countWords(text);

        if (words > maxWordsPerString)
            tonamorph::test::reportFailure(__FILE__, __LINE__, std::string(entry.id) + " has " + std::to_string(words) + " words: " + text);

        TONAMORPH_CHECK(!text.empty());
        TONAMORPH_CHECK(text.front() != ' ' && text.back() != ' ');
        TONAMORPH_CHECK(ids.insert(entry.id).second);   // no duplicate ids
    }

    TONAMORPH_CHECK(tableSize > 50);
    TONAMORPH_CHECK_EQ(countWords("That was your last free morph. Nothing happens unless you buy."), 11);
    TONAMORPH_CHECK_EQ(countWords("Your first morph. {key} · {bpm} BPM."), 6);
    TONAMORPH_CHECK_EQ(countWords("Engine's busy. Nothing was charged — try again shortly."), 8);
    TONAMORPH_CHECK_EQ(countWords(""), 0);
}

TONAMORPH_TEST(placeholdersAreFilled)
{
    TONAMORPH_CHECK_EQ(fill(celebrateFirstPurchase, "count", "50"),
                       std::string("50 morphs loaded. Thanks for backing a one-person shop."));
    TONAMORPH_CHECK_EQ(fill(fill(celebrateFirstMorph, "key", "F minor"), "bpm", "124"),
                       std::string("Your first morph. F minor · 124 BPM."));
    TONAMORPH_CHECK_EQ(fill(updateAvailable, "product", productName), std::string("Tonamorph {version} is available."));
    TONAMORPH_CHECK_EQ(fill("{x}{x}", "x", "{x}"), std::string("{x}{x}"));   // no re-expansion of inserted text
}

namespace
{
    /** True when the `Tonamorph` at `pos` sits inside a string literal on this line. */
    bool insideStringLiteral(const std::string& line, std::size_t pos)
    {
        bool inside = false;

        for (std::size_t i = 0; i < pos; ++i)
        {
            if (line[i] == '\\' && inside)
            {
                ++i;
                continue;
            }

            if (line[i] == '"')
                inside = !inside;
        }

        return inside;
    }
} // namespace

// The product name must be spelled only in Strings.h (as strings::productName) so the copy
// review sees every mention; JUCE identifiers such as TonamorphAudioProcessor are fine, and
// so are #include lines and a line carrying a "not user-facing" comment (the saved-state
// tag, which must never follow a rename).
TONAMORPH_TEST(noProductNameLiteralOutsideStringsHeader)
{
#ifdef TONAMORPH_SOURCE_DIR
    const std::filesystem::path root(TONAMORPH_SOURCE_DIR);
    TONAMORPH_CHECK(std::filesystem::is_directory(root));
    int filesScanned = 0;

    for (const auto& entry : std::filesystem::recursive_directory_iterator(root))
    {
        if (!entry.is_regular_file())
            continue;

        const auto extension = entry.path().extension().string();

        if (extension != ".cpp" && extension != ".h")
            continue;

        if (entry.path().filename() == "Strings.h")
            continue;

        ++filesScanned;
        std::ifstream in(entry.path());
        std::string line;
        int lineNumber = 0;
        bool inBlockComment = false;

        while (std::getline(in, line))
        {
            ++lineNumber;

            const auto firstNonSpace = line.find_first_not_of(" \t");

            if (firstNonSpace != std::string::npos && line[firstNonSpace] == '#')
                continue;

            if (line.find("not user-facing") != std::string::npos)
                continue;

            if (inBlockComment)
            {
                if (const auto end = line.find("*/"); end != std::string::npos)
                {
                    line = line.substr(end + 2);
                    inBlockComment = false;
                }
                else
                {
                    continue;
                }
            }

            if (const auto start = line.find("/*"); start != std::string::npos)
            {
                if (const auto end = line.find("*/", start + 2); end != std::string::npos)
                    line = line.substr(0, start) + line.substr(end + 2);
                else
                {
                    line = line.substr(0, start);
                    inBlockComment = true;
                }
            }

            if (const auto comment = line.find("//"); comment != std::string::npos && !insideStringLiteral(line, comment))
                line = line.substr(0, comment);

            for (auto pos = line.find(productName); pos != std::string::npos; pos = line.find(productName, pos + 1))
            {
                if (insideStringLiteral(line, pos))
                {
                    std::ostringstream message;
                    message << entry.path().filename().string() << ':' << lineNumber
                            << " spells the product name in a literal: " << line;
                    tonamorph::test::reportFailure(__FILE__, __LINE__, message.str());
                }
            }
        }
    }

    TONAMORPH_CHECK(filesScanned > 20);
#else
    tonamorph::test::reportFailure(__FILE__, __LINE__, "TONAMORPH_SOURCE_DIR is not defined for the test target");
#endif
}
