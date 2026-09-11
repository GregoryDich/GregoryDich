#include "TestFramework.h"

#include "Core/Envelope.h"

#include <cmath>
#include <vector>

namespace
{

constexpr double sampleRate = 44100.0;
constexpr double twoPi = 6.283185307179586;

std::vector<float> sine (double seconds, double frequency, double amplitude)
{
    const auto n = static_cast<std::size_t> (seconds * sampleRate);
    std::vector<float> out (n);

    for (std::size_t i = 0; i < n; ++i)
        out[i] = static_cast<float> (amplitude * std::sin (twoPi * frequency * static_cast<double> (i) / sampleRate));

    return out;
}

void checkWithinClampRange (const tonamorph::core::Adsr& adsr)
{
    TONAMORPH_CHECK (adsr.attackMs >= 1.0 && adsr.attackMs <= 2000.0);
    TONAMORPH_CHECK (adsr.decayMs >= 1.0 && adsr.decayMs <= 4000.0);
    TONAMORPH_CHECK (adsr.sustain >= 0.0 && adsr.sustain <= 1.0);
    TONAMORPH_CHECK (adsr.releaseMs >= 5.0 && adsr.releaseMs <= 5000.0);
}

} // namespace

TONAMORPH_TEST(envelopeOfSyntheticPluck)
{
    // 440 Hz with an exponential decay (tau = 300 ms) over 1.5 s.
    std::vector<float> pluck = sine (1.5, 440.0, 0.9);
    for (std::size_t i = 0; i < pluck.size(); ++i)
        pluck[i] = static_cast<float> (pluck[i] * std::exp (-static_cast<double> (i) / sampleRate / 0.3));

    const auto adsr = tonamorph::core::deriveAdsr (pluck.data(), static_cast<int> (pluck.size()), sampleRate);
    checkWithinClampRange (adsr);

    TONAMORPH_CHECK (adsr.attackMs <= 15.0);                         // instantaneous attack
    TONAMORPH_CHECK (adsr.decayMs >= 600.0 && adsr.decayMs <= 900.0); // peak -> median of the middle third (~750 ms)
    TONAMORPH_CHECK (adsr.sustain >= 0.04 && adsr.sustain <= 0.15);   // exp(-0.75 / 0.3) ~ 0.08
    TONAMORPH_CHECK (adsr.releaseMs >= 500.0 && adsr.releaseMs <= 900.0);
    TONAMORPH_CHECK (adsr.decayMs > adsr.attackMs);
}

TONAMORPH_TEST(envelopeOfSustainedToneThatStopsAbruptly)
{
    std::vector<float> tone = sine (1.0, 440.0, 0.5);
    tone.resize (static_cast<std::size_t> (1.5 * sampleRate), 0.0f);

    const auto adsr = tonamorph::core::deriveAdsr (tone.data(), static_cast<int> (tone.size()), sampleRate);
    checkWithinClampRange (adsr);

    TONAMORPH_CHECK (adsr.attackMs <= 15.0);
    TONAMORPH_CHECK (adsr.decayMs <= 60.0);
    TONAMORPH_CHECK (adsr.sustain >= 0.95);
    TONAMORPH_CHECK (adsr.releaseMs <= 20.0);
}

TONAMORPH_TEST(envelopeOfPadWithLinearAttackAndRelease)
{
    // 200 ms linear ramp, hold until 1.0 s, 300 ms linear fade-out.
    std::vector<float> pad = sine (1.3, 220.0, 0.5);
    for (std::size_t i = 0; i < pad.size(); ++i)
    {
        const double t = static_cast<double> (i) / sampleRate;
        double gain = 1.0;
        if (t < 0.2)
            gain = t / 0.2;
        else if (t > 1.0)
            gain = 1.0 - (t - 1.0) / 0.3;
        pad[i] = static_cast<float> (pad[i] * gain);
    }

    const auto adsr = tonamorph::core::deriveAdsr (pad.data(), static_cast<int> (pad.size()), sampleRate);
    checkWithinClampRange (adsr);

    TONAMORPH_CHECK (adsr.attackMs >= 150.0 && adsr.attackMs <= 210.0);   // 90 % of peak at 180 ms
    TONAMORPH_CHECK (adsr.sustain >= 0.95);
    TONAMORPH_CHECK (adsr.decayMs <= 60.0);
    TONAMORPH_CHECK (adsr.releaseMs >= 200.0 && adsr.releaseMs <= 320.0);
}

TONAMORPH_TEST(envelopeDegenerateInputsReturnDefaults)
{
    const tonamorph::core::Adsr defaults;
    const auto isDefault = [&defaults] (const tonamorph::core::Adsr& adsr)
    {
        return adsr.attackMs == defaults.attackMs && adsr.decayMs == defaults.decayMs
            && adsr.sustain == defaults.sustain && adsr.releaseMs == defaults.releaseMs;
    };

    const std::vector<float> silence (44100, 0.0f);
    TONAMORPH_CHECK (isDefault (tonamorph::core::deriveAdsr (silence.data(), 44100, sampleRate)));

    const std::vector<float> quiet (44100, 0.0005f);   // below -60 dBFS
    TONAMORPH_CHECK (isDefault (tonamorph::core::deriveAdsr (quiet.data(), 44100, sampleRate)));

    const std::vector<float> tiny (100, 0.5f);         // shorter than three hops
    TONAMORPH_CHECK (isDefault (tonamorph::core::deriveAdsr (tiny.data(), 100, sampleRate)));

    TONAMORPH_CHECK (isDefault (tonamorph::core::deriveAdsr (nullptr, 0, sampleRate)));
    TONAMORPH_CHECK (isDefault (tonamorph::core::deriveAdsr (tiny.data(), 100, 0.0)));
}
