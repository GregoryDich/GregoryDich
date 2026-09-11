#pragma once

/**
 * The bundled demo morph (GTM Appendix B §1): four short A-minor stems, a score and a
 * result.json generated at configure time (Resources/generate_demo.py) and embedded as
 * DemoData. Installed into the job cache as job "demo" so JobClient::loadCachedJob plays
 * it like any cached result — before sign-in, without a credit and without the network.
 */

#include <JuceHeader.h>

namespace tonamorph
{

class DemoMorph
{
public:
    static constexpr const char* jobId = "demo";

    /** Writes the embedded files into `<cacheRoot>/demo` when they are missing or differ
        in size from the bundle. Returns true when every file is in place afterwards. */
    static bool install (const juce::File& cacheRoot);

private:
    DemoMorph() = delete;
};

} // namespace tonamorph
