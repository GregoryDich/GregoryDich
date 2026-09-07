#include "Cloud/Models.h"

namespace snapplay::cloud
{

//==============================================================================
std::optional<ApiError> ApiError::fromJson (const juce::var& json)
{
    juce::ignoreUnused (json);
    return std::nullopt;
}

juce::var ApiError::toVar() const
{
    return {};
}

ApiError ApiError::transport (const juce::String& message)
{
    ApiError error;
    error.code = "network_error";
    error.message = message;
    return error;
}

ApiError ApiError::cancelled()
{
    ApiError error;
    error.code = "cancelled";
    error.message = "Request cancelled";
    return error;
}

ApiError ApiError::fromHttpStatus (int status, const juce::String& body)
{
    juce::ignoreUnused (body);
    ApiError error;
    error.httpStatus = status;
    return error;
}

//==============================================================================
std::optional<CreditBalance> CreditBalance::fromJson (const juce::var& json)
{
    juce::ignoreUnused (json);
    return std::nullopt;
}

juce::var CreditBalance::toVar() const
{
    return {};
}

std::optional<UserInfo> UserInfo::fromJson (const juce::var& json)
{
    juce::ignoreUnused (json);
    return std::nullopt;
}

juce::var UserInfo::toVar() const
{
    return {};
}

std::optional<AuthTokens> AuthTokens::fromJson (const juce::var& json)
{
    juce::ignoreUnused (json);
    return std::nullopt;
}

juce::var AuthTokens::toVar() const
{
    return {};
}

std::optional<MeResponse> MeResponse::fromJson (const juce::var& json)
{
    juce::ignoreUnused (json);
    return std::nullopt;
}

juce::var MeResponse::toVar() const
{
    return {};
}

std::optional<PlanInfo> PlanInfo::fromJson (const juce::var& json)
{
    juce::ignoreUnused (json);
    return std::nullopt;
}

juce::var PlanInfo::toVar() const
{
    return {};
}

std::optional<std::vector<PlanInfo>> PlanInfo::listFromJson (const juce::var& json)
{
    juce::ignoreUnused (json);
    return std::nullopt;
}

//==============================================================================
juce::String toString (JobState state)
{
    switch (state)
    {
        case JobState::Queued:    return "queued";
        case JobState::Running:   return "running";
        case JobState::Succeeded: return "succeeded";
        case JobState::Failed:    return "failed";
        case JobState::Cancelled: return "cancelled";
    }

    return "queued";
}

juce::String toString (JobStage stage)
{
    switch (stage)
    {
        case JobStage::Upload:     return "upload";
        case JobStage::Separate:   return "separate";
        case JobStage::Transcribe: return "transcribe";
        case JobStage::Analyze:    return "analyze";
        case JobStage::Package:    return "package";
        case JobStage::Done:       return "done";
    }

    return "upload";
}

std::optional<JobState> jobStateFromString (const juce::String& text)
{
    juce::ignoreUnused (text);
    return std::nullopt;
}

std::optional<JobStage> jobStageFromString (const juce::String& text)
{
    juce::ignoreUnused (text);
    return std::nullopt;
}

std::optional<JobOptions> JobOptions::fromJson (const juce::var& json)
{
    juce::ignoreUnused (json);
    return std::nullopt;
}

juce::var JobOptions::toVar() const
{
    return {};
}

juce::String JobOptions::toJsonString() const
{
    return juce::JSON::toString (toVar(), true);
}

std::optional<JobSubmitResponse> JobSubmitResponse::fromJson (const juce::var& json)
{
    juce::ignoreUnused (json);
    return std::nullopt;
}

juce::var JobSubmitResponse::toVar() const
{
    return {};
}

std::optional<InputInfo> InputInfo::fromJson (const juce::var& json)
{
    juce::ignoreUnused (json);
    return std::nullopt;
}

juce::var InputInfo::toVar() const
{
    return {};
}

std::optional<KeyInfo> KeyInfo::fromJson (const juce::var& json)
{
    juce::ignoreUnused (json);
    return std::nullopt;
}

KeyInfo KeyInfo::fromCore (const core::KeyInfo& key)
{
    KeyInfo info;
    info.root = juce::String (key.root);
    info.mode = juce::String (key.mode);
    info.rootMidi = key.rootMidi;
    info.confidence = key.confidence;
    info.scalePitchClasses = key.scalePitchClasses;
    return info;
}

juce::var KeyInfo::toVar() const
{
    return {};
}

core::KeyInfo KeyInfo::toCore() const
{
    core::KeyInfo key;
    key.root = root.toStdString();
    key.mode = mode.toStdString();
    key.rootMidi = rootMidi;
    key.confidence = confidence;
    key.scalePitchClasses = scalePitchClasses;
    return key;
}

std::optional<Analysis> Analysis::fromJson (const juce::var& json)
{
    juce::ignoreUnused (json);
    return std::nullopt;
}

juce::var Analysis::toVar() const
{
    return {};
}

std::optional<StemInfo> StemInfo::fromJson (const juce::var& json)
{
    juce::ignoreUnused (json);
    return std::nullopt;
}

juce::var StemInfo::toVar() const
{
    return {};
}

std::optional<MidiInfo> MidiInfo::fromJson (const juce::var& json)
{
    juce::ignoreUnused (json);
    return std::nullopt;
}

juce::var MidiInfo::toVar() const
{
    return {};
}

std::optional<JobResult> JobResult::fromJson (const juce::var& json)
{
    juce::ignoreUnused (json);
    return std::nullopt;
}

juce::var JobResult::toVar() const
{
    return {};
}

const StemInfo* JobResult::findStem (const juce::String& stemName) const noexcept
{
    for (const auto& stem : stems)
        if (stem.name == stemName)
            return &stem;

    return nullptr;
}

bool JobResult::isExpired (juce::Time now) const
{
    juce::ignoreUnused (now);
    return false;
}

std::optional<JobStatus> JobStatus::fromJson (const juce::var& json)
{
    juce::ignoreUnused (json);
    return std::nullopt;
}

juce::var JobStatus::toVar() const
{
    return {};
}

std::optional<JobEvent> JobEvent::fromSse (const juce::String& eventName, const juce::var& data)
{
    juce::ignoreUnused (eventName, data);
    return std::nullopt;
}

std::optional<ApiKeyInfo> ApiKeyInfo::fromJson (const juce::var& json)
{
    juce::ignoreUnused (json);
    return std::nullopt;
}

juce::var ApiKeyInfo::toVar() const
{
    return {};
}

//==============================================================================
std::optional<core::Adsr> adsrFromJson (const juce::var& json)
{
    juce::ignoreUnused (json);
    return std::nullopt;
}

juce::var adsrToVar (const core::Adsr& adsr)
{
    juce::ignoreUnused (adsr);
    return {};
}

std::optional<core::Slice> sliceFromJson (const juce::var& json)
{
    juce::ignoreUnused (json);
    return std::nullopt;
}

juce::var sliceToVar (const core::Slice& slice)
{
    juce::ignoreUnused (slice);
    return {};
}

std::optional<core::Note> noteFromJson (const juce::var& json)
{
    juce::ignoreUnused (json);
    return std::nullopt;
}

juce::var noteToVar (const core::Note& note)
{
    juce::ignoreUnused (note);
    return {};
}

std::optional<core::Track> trackFromJson (const juce::var& json)
{
    juce::ignoreUnused (json);
    return std::nullopt;
}

juce::var trackToVar (const core::Track& track)
{
    juce::ignoreUnused (track);
    return {};
}

} // namespace snapplay::cloud
