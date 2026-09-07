#pragma once

/**
 * Wire models for the SnapPlay API (docs/API_CONTRACT.md v2).
 *
 * Every model parses with `static std::optional<T> fromJson (const juce::var&)` (returns
 * nullopt when required fields are missing or mistyped) and serialises with
 * `juce::var toVar() const` (the exact contract shape, snake_case keys). Types that the
 * core algorithms consume (`Note`, `Track`, `Adsr`, `Slice`) are the snapplay::core
 * structs; their JSON helpers are free functions at the end of this file.
 */

#include <JuceHeader.h>

#include "Core/Types.h"

#include <array>
#include <optional>
#include <vector>

namespace snapplay::cloud
{

/** The four Demucs stem names, in the order the API and the `category` parameter use
    (the UI label "Synth" maps to `other`). */
inline constexpr std::array<const char*, 4> stemNames { "bass", "drums", "other", "vocals" };

//==============================================================================
/** Contract §5 error envelope, plus client-side transport errors. */
struct ApiError
{
    juce::String code;        ///< e.g. "insufficient_credits", "network_error", "cancelled"
    juce::String message;
    juce::var details;        ///< optional `details` object (may be void)
    int httpStatus = 0;       ///< HTTP status that carried the error; 0 for transport errors

    /** Parses either the `{ "error": { ... } }` envelope or the inner object. */
    static std::optional<ApiError> fromJson (const juce::var& json);
    juce::var toVar() const;

    /** A connection/timeout failure (`code == "network_error"`). */
    static ApiError transport (const juce::String& message);
    /** The request was cancelled by the client (`code == "cancelled"`). */
    static ApiError cancelled();
    /** Maps a bare HTTP status (no JSON envelope) to the contract §5 code table. */
    static ApiError fromHttpStatus (int status, const juce::String& body);

    bool isInsufficientCredits() const noexcept { return code == "insufficient_credits"; }
    bool isUnauthorized() const noexcept       { return httpStatus == 401; }
};

//==============================================================================
/** `balance` object (contract §1 `/v1/me`, §2 job responses). The UI shows `available`. */
struct CreditBalance
{
    int credits = 0;
    int reserved = 0;
    int available = 0;
    std::optional<juce::String> subscriptionRenewsAt;   ///< RFC 3339, subscription plans only

    static std::optional<CreditBalance> fromJson (const juce::var& json);
    juce::var toVar() const;
};

/** `user` object. `plan` is empty in auth responses and set by `/v1/me`. */
struct UserInfo
{
    juce::String id;      ///< UUID
    juce::String email;
    juce::String plan;    ///< "free" | "credits" | "subscription" | "" (unknown)

    static std::optional<UserInfo> fromJson (const juce::var& json);
    juce::var toVar() const;
};

/** `POST /v1/auth/token` and `POST /v1/auth/refresh` response. */
struct AuthTokens
{
    juce::String accessToken;
    juce::String refreshToken;
    int expiresIn = 3600;                ///< seconds from issue
    juce::String tokenType { "bearer" };
    UserInfo user;

    static std::optional<AuthTokens> fromJson (const juce::var& json);
    juce::var toVar() const;
};

/** `GET /v1/me` response. */
struct MeResponse
{
    UserInfo user;
    CreditBalance balance;

    static std::optional<MeResponse> fromJson (const juce::var& json);
    juce::var toVar() const;
};

/** One entry of `GET /v1/plans` (contract §3). */
struct PlanInfo
{
    juce::String id;                           ///< "free" | "pack_50" | "sub_monthly" | ...
    juce::String name;
    int credits = 0;
    double priceUsd = 0.0;
    std::optional<juce::String> interval;      ///< "month" for subscriptions, nullopt otherwise
    std::optional<juce::String> checkoutUrl;   ///< nullopt for the free plan

    static std::optional<PlanInfo> fromJson (const juce::var& json);
    juce::var toVar() const;

    /** Parses the `{ "plans": [ ... ] }` envelope. */
    static std::optional<std::vector<PlanInfo>> listFromJson (const juce::var& json);
    bool isSubscription() const noexcept { return interval.has_value(); }
};

//==============================================================================
/** `jobs.status` lifecycle (contract §6). */
enum class JobState { Queued, Running, Succeeded, Failed, Cancelled };

/** Pipeline stage reported in JobStatus / SSE progress events (contract §2). */
enum class JobStage { Upload, Separate, Transcribe, Analyze, Package, Done };

juce::String toString (JobState state);
juce::String toString (JobStage stage);
std::optional<JobState> jobStateFromString (const juce::String& text);
std::optional<JobStage> jobStageFromString (const juce::String& text);

/** The `options` JSON of `POST /v1/jobs` (contract §2). Empty arrays mean server defaults. */
struct JobOptions
{
    std::optional<int> clientSampleRate;
    juce::StringArray stems;              ///< subset of stemNames; empty = all four
    juce::StringArray transcribe;         ///< subset of stemNames; empty = server default
    bool drumSlices = true;
    int targetRootMidi = 48;
    juce::String idempotencyKey;          ///< client UUID; empty = none

    static std::optional<JobOptions> fromJson (const juce::var& json);
    juce::var toVar() const;
    /** Compact JSON text for the multipart `options` field. */
    juce::String toJsonString() const;
};

/** `POST /v1/jobs` 202 response. */
struct JobSubmitResponse
{
    juce::String jobId;
    JobState status = JobState::Queued;
    int creditsReserved = 1;
    CreditBalance balance;

    static std::optional<JobSubmitResponse> fromJson (const juce::var& json);
    juce::var toVar() const;
};

/** `JobResult.input`. */
struct InputInfo
{
    double durationSeconds = 0.0;
    int sampleRate = 44100;
    int channels = 2;
    bool truncated = false;   ///< input exceeded 60 s and was cut server-side

    static std::optional<InputInfo> fromJson (const juce::var& json);
    juce::var toVar() const;
};

/** `JobResult.analysis.key`. Same fields as core::KeyInfo; use toCore() for the algorithms. */
struct KeyInfo
{
    juce::String root;                    ///< e.g. "F"
    juce::String mode;                    ///< "major" | "minor"
    int rootMidi = 60;
    double confidence = 0.0;
    std::vector<int> scalePitchClasses;   ///< 0..11

    static std::optional<KeyInfo> fromJson (const juce::var& json);
    static KeyInfo fromCore (const core::KeyInfo& key);
    juce::var toVar() const;
    core::KeyInfo toCore() const;
};

/** `JobResult.analysis`. */
struct Analysis
{
    double bpm = 120.0;
    double bpmConfidence = 0.0;
    KeyInfo key;
    std::vector<double> downbeatsSeconds;
    std::vector<double> beatsSeconds;

    static std::optional<Analysis> fromJson (const juce::var& json);
    juce::var toVar() const;
};

/** One entry of `JobResult.stems`. */
struct StemInfo
{
    juce::String name;                       ///< bass | drums | other | vocals
    juce::String url;                        ///< signed URL, valid until JobResult::expiresAt
    juce::String format { "wav" };
    int sampleRate = 44100;
    int channels = 2;
    double durationSeconds = 0.0;
    int rootMidi = 48;
    double rootConfidence = 0.0;
    double peakDb = 0.0;
    double rmsDb = 0.0;
    std::vector<double> transientsSeconds;
    std::optional<core::Adsr> suggestedAdsr;   ///< nullopt → derive with core::deriveAdsr
    std::vector<core::Slice> slices;           ///< drums only, when drum_slices was requested

    static std::optional<StemInfo> fromJson (const juce::var& json);
    juce::var toVar() const;
};

/** `JobResult.midi`. */
struct MidiInfo
{
    juce::String url;      ///< signed URL of score.mid
    int ppq = 480;
    double bpm = 120.0;
    std::vector<core::Track> tracks;

    static std::optional<MidiInfo> fromJson (const juce::var& json);
    juce::var toVar() const;
};

/** Contract §2 JobResult. */
struct JobResult
{
    juce::String jobId;
    int creditsCharged = 1;
    int balanceAfter = 0;
    InputInfo input;
    Analysis analysis;
    std::vector<StemInfo> stems;
    MidiInfo midi;
    juce::String expiresAt;   ///< RFC 3339; signed URLs die after this

    static std::optional<JobResult> fromJson (const juce::var& json);
    juce::var toVar() const;

    /** The stem with the given contract name, or nullptr. */
    const StemInfo* findStem (const juce::String& stemName) const noexcept;
    /** True when `expiresAt` is in the past (signed URLs can no longer be downloaded). */
    bool isExpired (juce::Time now = juce::Time::getCurrentTime()) const;
};

/** `GET /v1/jobs/{id}` response and the payload of SSE `result` events. */
struct JobStatus
{
    juce::String jobId;
    JobState status = JobState::Queued;
    JobStage stage = JobStage::Upload;
    double progress = 0.0;                 ///< 0..1
    juce::String createdAt;
    juce::String startedAt;
    juce::String finishedAt;
    std::optional<ApiError> error;         ///< set when status == Failed
    std::optional<JobResult> result;       ///< set when status == Succeeded

    static std::optional<JobStatus> fromJson (const juce::var& json);
    juce::var toVar() const;

    bool isTerminal() const noexcept
    {
        return status == JobState::Succeeded || status == JobState::Failed || status == JobState::Cancelled;
    }
};

/** One Server-Sent Event from `GET /v1/jobs/{id}/events` (contract §2). */
struct JobEvent
{
    enum class Type { Progress, Result, Error };

    Type type = Type::Progress;
    JobStage stage = JobStage::Upload;     ///< Progress events
    double progress = 0.0;                 ///< Progress events, 0..1
    std::optional<JobStatus> status;       ///< Result events
    std::optional<ApiError> error;         ///< Error events

    /** Builds an event from the SSE `event:` name and its parsed `data:` JSON;
        nullopt for unknown event names or malformed payloads. */
    static std::optional<JobEvent> fromSse (const juce::String& eventName, const juce::var& data);
    bool endsStream() const noexcept { return type != Type::Progress; }
};

/** `POST /v1/api-keys` response (contract §11). `key` is the plaintext, returned once. */
struct ApiKeyInfo
{
    juce::String id;
    juce::String name;
    juce::String prefix;     ///< "sp_live_" + first chars, safe to display
    juce::String key;        ///< full plaintext key; only present on creation
    juce::String createdAt;

    static std::optional<ApiKeyInfo> fromJson (const juce::var& json);
    juce::var toVar() const;
};

//==============================================================================
// JSON helpers for the JUCE-free core structs.

std::optional<core::Adsr> adsrFromJson (const juce::var& json);
juce::var adsrToVar (const core::Adsr& adsr);

std::optional<core::Slice> sliceFromJson (const juce::var& json);
juce::var sliceToVar (const core::Slice& slice);

std::optional<core::Note> noteFromJson (const juce::var& json);
juce::var noteToVar (const core::Note& note);

std::optional<core::Track> trackFromJson (const juce::var& json);
juce::var trackToVar (const core::Track& track);

} // namespace snapplay::cloud
