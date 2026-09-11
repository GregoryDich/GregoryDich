#include "TestFramework.h"

#include "Core/SemanticVersion.h"

using tonamorph::core::compareVersions;
using tonamorph::core::isBelowMinimumVersion;
using tonamorph::core::isNewerVersion;
using tonamorph::core::parseSemanticVersion;

TONAMORPH_TEST(semanticVersionParsesCommonShapes)
{
    const auto full = parseSemanticVersion("1.2.3");
    TONAMORPH_CHECK(full.has_value());
    TONAMORPH_CHECK_EQ(full->major, 1);
    TONAMORPH_CHECK_EQ(full->minor, 2);
    TONAMORPH_CHECK_EQ(full->patch, 3);
    TONAMORPH_CHECK(full->isRelease());

    const auto tagged = parseSemanticVersion(" v0.1.0 ");
    TONAMORPH_CHECK(tagged.has_value());
    TONAMORPH_CHECK_EQ(tagged->minor, 1);

    const auto two = parseSemanticVersion("2.5");
    TONAMORPH_CHECK(two.has_value());
    TONAMORPH_CHECK_EQ(two->patch, 0);

    const auto pre = parseSemanticVersion("1.0.0-rc1");
    TONAMORPH_CHECK(pre.has_value());
    TONAMORPH_CHECK_EQ(pre->prerelease, std::string("rc1"));

    TONAMORPH_CHECK(!parseSemanticVersion("").has_value());
    TONAMORPH_CHECK(!parseSemanticVersion("abc").has_value());
    TONAMORPH_CHECK(!parseSemanticVersion("1..2").has_value());
    TONAMORPH_CHECK(!parseSemanticVersion("1.2.3.4").has_value());
    TONAMORPH_CHECK(!parseSemanticVersion("1.2.3-").has_value());
}

TONAMORPH_TEST(semanticVersionOrdersNumericallyNotLexically)
{
    TONAMORPH_CHECK(isNewerVersion("1.10.0", "1.9.9"));
    TONAMORPH_CHECK(isNewerVersion("2.0.0", "1.99.99"));
    TONAMORPH_CHECK(isNewerVersion("0.1.1", "0.1.0"));
    TONAMORPH_CHECK(!isNewerVersion("0.1.0", "0.1.0"));
    TONAMORPH_CHECK(!isNewerVersion("0.0.9", "0.1.0"));
    TONAMORPH_CHECK(!isNewerVersion("garbage", "0.1.0"));   // unparsable never shows a banner
    TONAMORPH_CHECK(!isNewerVersion("1.0.0", ""));
}

TONAMORPH_TEST(semanticVersionPrereleaseOrdersBeforeRelease)
{
    const auto release = *parseSemanticVersion("1.0.0");
    const auto rc = *parseSemanticVersion("1.0.0-rc1");
    const auto beta = *parseSemanticVersion("1.0.0-beta");

    TONAMORPH_CHECK(compareVersions(rc, release) < 0);
    TONAMORPH_CHECK(compareVersions(release, rc) > 0);
    TONAMORPH_CHECK(compareVersions(beta, rc) < 0);
    TONAMORPH_CHECK_EQ(compareVersions(rc, rc), 0);
    TONAMORPH_CHECK(isNewerVersion("1.0.0", "1.0.0-rc1"));
}

TONAMORPH_TEST(minimumSupportedGate)
{
    TONAMORPH_CHECK(isBelowMinimumVersion("0.1.0", "0.2.0"));
    TONAMORPH_CHECK(!isBelowMinimumVersion("0.2.0", "0.2.0"));
    TONAMORPH_CHECK(!isBelowMinimumVersion("0.3.0", "0.2.0"));
    TONAMORPH_CHECK(!isBelowMinimumVersion("0.1.0", ""));   // no minimum announced: never block
}
