#include "App/DemoMorph.h"

#include "Cloud/JobClient.h"
#include "DemoData.h"

namespace tonamorph
{

bool DemoMorph::install (const juce::File& cacheRoot)
{
    struct Asset
    {
        const char* fileName;
        const char* data;
        int size;
    };

    const Asset assets[] = {
        { "bass.wav",    DemoData::bass_wav,    DemoData::bass_wavSize },
        { "drums.wav",   DemoData::drums_wav,   DemoData::drums_wavSize },
        { "other.wav",   DemoData::other_wav,   DemoData::other_wavSize },
        { "vocals.wav",  DemoData::vocals_wav,  DemoData::vocals_wavSize },
        { "score.mid",   DemoData::score_mid,   DemoData::score_midSize },
        { "result.json", DemoData::result_json, DemoData::result_jsonSize },
    };

    const auto directory = cloud::JobClient::jobDirectoryFor (cacheRoot, jobId);

    if (! directory.createDirectory().wasOk())
        return false;

    bool ok = true;

    for (const auto& asset : assets)
    {
        const auto file = directory.getChildFile (asset.fileName);

        if (file.existsAsFile() && file.getSize() == static_cast<juce::int64> (asset.size))
            continue;

        ok = file.replaceWithData (asset.data, static_cast<size_t> (asset.size)) && ok;
    }

    return ok;
}

} // namespace tonamorph
