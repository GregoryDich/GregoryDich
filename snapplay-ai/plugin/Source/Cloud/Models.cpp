#include "Cloud/Models.h"

namespace snapplay::cloud
{

namespace
{

//==============================================================================
// Tolerant readers: a missing/null optional field keeps the caller's default, a missing
// required field or a value of the wrong type makes the reader return false.

bool isNumber (const juce::var& value) noexcept
{
    return value.isInt() || value.isInt64() || value.isDouble();
}

bool isMissing (const juce::var& value) noexcept
{
    return value.isVoid() || value.isUndefined();
}

juce::var get (const juce::var& object, const char* key)
{
    return object.isObject() ? object.getProperty (juce::Identifier (key), juce::var()) : juce::var();
}

bool readInt (const juce::var& object, const char* key, int& out, bool required = true)
{
    const auto value = get (object, key);

    if (isMissing (value))
        return ! required;

    if (! isNumber (value))
        return false;

    out = static_cast<int> (value);
    return true;
}

bool readDouble (const juce::var& object, const char* key, double& out, bool required = true)
{
    const auto value = get (object, key);

    if (isMissing (value))
        return ! required;

    if (! isNumber (value))
        return false;

    out = static_cast<double> (value);
    return true;
}

bool readBool (const juce::var& object, const char* key, bool& out, bool required = true)
{
    const auto value = get (object, key);

    if (isMissing (value))
        return ! required;

    if (! value.isBool())
        return false;

    out = static_cast<bool> (value);
    return true;
}

bool readString (const juce::var& object, const char* key, juce::String& out, bool required = true)
{
    const auto value = get (object, key);

    if (isMissing (value))
        return ! required;

    if (! value.isString())
        return false;

    out = value.toString();
    return true;
}

bool readOptionalString (const juce::var& object, const char* key, std::optional<juce::String>& out)
{
    const auto value = get (object, key);

    if (isMissing (value))
    {
        out.reset();
        return true;
    }

    if (! value.isString())
        return false;

    out = value.toString();
    return true;
}

bool readOptionalInt (const juce::var& object, const char* key, std::optional<int>& out)
{
    const auto value = get (object, key);

    if (isMissing (value))
    {
        out.reset();
        return true;
    }

    if (! isNumber (value))
        return false;

    out = static_cast<int> (value);
    return true;
}

bool readDoubleArray (const juce::var& object, const char* key, std::vector<double>& out)
{
    const auto value = get (object, key);
    out.clear();

    if (isMissing (value))
        return true;

    if (! value.isArray())
        return false;

    for (const auto& item : *value.getArray())
    {
        if (! isNumber (item))
            return false;

        out.push_back (static_cast<double> (item));
    }

    return true;
}

bool readIntArray (const juce::var& object, const char* key, std::vector<int>& out)
{
    const auto value = get (object, key);
    out.clear();

    if (isMissing (value))
        return true;

    if (! value.isArray())
        return false;

    for (const auto& item : *value.getArray())
    {
        if (! isNumber (item))
            return false;

        out.push_back (static_cast<int> (item));
    }

    return true;
}

bool readStringArray (const juce::var& object, const char* key, juce::StringArray& out)
{
    const auto value = get (object, key);
    out.clear();

    if (isMissing (value))
        return true;

    if (! value.isArray())
        return false;

    for (const auto& item : *value.getArray())
    {
        if (! item.isString())
            return false;

        out.add (item.toString());
    }

    return true;
}

template <typename T>
bool readObject (const juce::var& object, const char* key, T& out,
                 std::optional<T> (*parse) (const juce::var&), bool required = true)
{
    const auto value = get (object, key);

    if (isMissing (value))
        return ! required;

    if (! value.isObject())
        return false;

    auto parsed = parse (value);

    if (! parsed.has_value())
        return false;

    out = std::move (*parsed);
    return true;
}

template <typename T>
bool readOptionalObject (const juce::var& object, const char* key, std::optional<T>& out,
                         std::optional<T> (*parse) (const juce::var&))
{
    const auto value = get (object, key);

    if (isMissing (value))
    {
        out.reset();
        return true;
    }

    if (! value.isObject())
        return false;

    out = parse (value);
    return out.has_value();
}

template <typename T>
bool readObjectArray (const juce::var& object, const char* key, std::vector<T>& out,
                      std::optional<T> (*parse) (const juce::var&), bool required = true)
{
    const auto value = get (object, key);
    out.clear();

    if (isMissing (value))
        return ! required;

    if (! value.isArray())
        return false;

    for (const auto& item : *value.getArray())
    {
        auto parsed = parse (item);

        if (! parsed.has_value())
            return false;

        out.push_back (std::move (*parsed));
    }

    return true;
}

//==============================================================================
// Writers.

class ObjectBuilder
{
public:
    ObjectBuilder() : object (new juce::DynamicObject()) {}

    ObjectBuilder& set (const char* key, const juce::var& value)
    {
        object->setProperty (juce::Identifier (key), value);
        return *this;
    }

    juce::var build() const { return juce::var (object.get()); }

private:
    juce::DynamicObject::Ptr object;
};

template <typename T, typename Fn>
juce::var arrayToVar (const std::vector<T>& items, Fn&& toVar)
{
    juce::Array<juce::var> array;
    array.ensureStorageAllocated (static_cast<int> (items.size()));

    for (const auto& item : items)
        array.add (toVar (item));

    return juce::var (array);
}

juce::var doubleArrayToVar (const std::vector<double>& items)
{
    return arrayToVar (items, [] (double v) { return juce::var (v); });
}

juce::var intArrayToVar (const std::vector<int>& items)
{
    return arrayToVar (items, [] (int v) { return juce::var (v); });
}

juce::var stringArrayToVar (const juce::StringArray& items)
{
    juce::Array<juce::var> array;

    for (const auto& item : items)
        array.add (item);

    return juce::var (array);
}

juce::var nullableString (const juce::String& text)
{
    return text.isEmpty() ? juce::var() : juce::var (text);
}

juce::var nullableString (const std::optional<juce::String>& text)
{
    return text.has_value() ? juce::var (*text) : juce::var();
}

/** The inner `{ code, message, details }` object shared by the §5 envelope, JobStatus.error
    and SSE error events. */
juce::var errorBodyToVar (const ApiError& error)
{
    ObjectBuilder body;
    body.set ("code", error.code).set ("message", error.message);

    if (error.details.isObject())
        body.set ("details", error.details);

    return body.build();
}

/** RFC 3339 with any number of fractional-second digits (juce::Time only accepts three). */
std::optional<juce::Time> parseRfc3339 (const juce::String& text)
{
    auto normalised = text.trim();

    if (normalised.isEmpty())
        return std::nullopt;

    const int dot = normalised.indexOfChar ('.');

    if (dot >= 0)
    {
        int end = dot + 1;

        while (end < normalised.length() && juce::CharacterFunctions::isDigit (normalised[end]))
            ++end;

        const auto fraction = (normalised.substring (dot + 1, end) + "000").substring (0, 3);
        normalised = normalised.substring (0, dot + 1) + fraction + normalised.substring (end);
    }

    const auto time = juce::Time::fromISO8601 (normalised);

    if (time.toMilliseconds() == 0)
        return std::nullopt;

    return time;
}

} // namespace

//==============================================================================
std::optional<ApiError> ApiError::fromJson (const juce::var& json)
{
    if (! json.isObject())
        return std::nullopt;

    const auto envelope = get (json, "error");
    const juce::var& source = envelope.isObject() ? envelope : json;

    ApiError error;

    if (! readString (source, "code", error.code) || ! readString (source, "message", error.message))
        return std::nullopt;

    const auto details = get (source, "details");
    error.details = details.isObject() ? details : juce::var();
    return error;
}

juce::var ApiError::toVar() const
{
    return ObjectBuilder().set ("error", errorBodyToVar (*this)).build();
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
    juce::var parsed;

    if (body.isNotEmpty() && juce::JSON::parse (body, parsed).wasOk())
    {
        if (auto error = fromJson (parsed))
        {
            error->httpStatus = status;
            return *error;
        }
    }

    ApiError error;
    error.httpStatus = status;

    switch (status)
    {
        case 400: error.code = "bad_request";            error.message = "The request was rejected by the server";      break;
        case 401: error.code = "unauthorized";           error.message = "Please sign in to continue";                  break;
        case 402: error.code = "insufficient_credits";   error.message = "You have no credits left";                     break;
        case 404: error.code = "not_found";              error.message = "Not found";                                    break;
        case 409: error.code = "conflict";               error.message = "The job is already running";                   break;
        case 413: error.code = "payload_too_large";      error.message = "The audio file is larger than 10 MB";          break;
        case 415: error.code = "unsupported_media_type"; error.message = "Unsupported audio format";                     break;
        case 422: error.code = "validation_error";       error.message = "Invalid request";                              break;
        case 429: error.code = "rate_limited";           error.message = "Too many requests, please try again shortly";  break;
        case 500: error.code = "internal_error";         error.message = "The server hit an internal error";             break;
        case 503: error.code = "worker_unavailable";     error.message = "The processing service is temporarily unavailable"; break;
        default:  error.code = "http_error";             error.message = "Request failed (HTTP " + juce::String (status) + ")"; break;
    }

    return error;
}

//==============================================================================
std::optional<CreditBalance> CreditBalance::fromJson (const juce::var& json)
{
    CreditBalance balance;

    if (! readInt (json, "credits", balance.credits)
        || ! readInt (json, "reserved", balance.reserved)
        || ! readInt (json, "available", balance.available)
        || ! readOptionalString (json, "subscription_renews_at", balance.subscriptionRenewsAt))
        return std::nullopt;

    return balance;
}

juce::var CreditBalance::toVar() const
{
    return ObjectBuilder()
        .set ("credits", credits)
        .set ("reserved", reserved)
        .set ("available", available)
        .set ("subscription_renews_at", nullableString (subscriptionRenewsAt))
        .build();
}

std::optional<UserInfo> UserInfo::fromJson (const juce::var& json)
{
    UserInfo user;

    if (! readString (json, "id", user.id)
        || ! readString (json, "email", user.email)
        || ! readString (json, "plan", user.plan, false))
        return std::nullopt;

    return user;
}

juce::var UserInfo::toVar() const
{
    ObjectBuilder builder;
    builder.set ("id", id).set ("email", email);

    if (plan.isNotEmpty())
        builder.set ("plan", plan);

    return builder.build();
}

std::optional<AuthTokens> AuthTokens::fromJson (const juce::var& json)
{
    AuthTokens tokens;

    if (! readString (json, "access_token", tokens.accessToken)
        || ! readString (json, "refresh_token", tokens.refreshToken)
        || ! readInt (json, "expires_in", tokens.expiresIn, false)
        || ! readString (json, "token_type", tokens.tokenType, false)
        || ! readObject (json, "user", tokens.user, &UserInfo::fromJson))
        return std::nullopt;

    if (tokens.accessToken.isEmpty() || tokens.refreshToken.isEmpty())
        return std::nullopt;

    return tokens;
}

juce::var AuthTokens::toVar() const
{
    return ObjectBuilder()
        .set ("access_token", accessToken)
        .set ("refresh_token", refreshToken)
        .set ("expires_in", expiresIn)
        .set ("token_type", tokenType)
        .set ("user", user.toVar())
        .build();
}

std::optional<MeResponse> MeResponse::fromJson (const juce::var& json)
{
    MeResponse me;

    if (! readObject (json, "user", me.user, &UserInfo::fromJson)
        || ! readObject (json, "balance", me.balance, &CreditBalance::fromJson))
        return std::nullopt;

    return me;
}

juce::var MeResponse::toVar() const
{
    return ObjectBuilder().set ("user", user.toVar()).set ("balance", balance.toVar()).build();
}

std::optional<PlanInfo> PlanInfo::fromJson (const juce::var& json)
{
    PlanInfo plan;

    if (! readString (json, "id", plan.id)
        || ! readString (json, "name", plan.name)
        || ! readInt (json, "credits", plan.credits)
        || ! readDouble (json, "price_usd", plan.priceUsd)
        || ! readOptionalString (json, "interval", plan.interval)
        || ! readOptionalString (json, "checkout_url", plan.checkoutUrl))
        return std::nullopt;

    return plan;
}

juce::var PlanInfo::toVar() const
{
    return ObjectBuilder()
        .set ("id", id)
        .set ("name", name)
        .set ("credits", credits)
        .set ("price_usd", priceUsd)
        .set ("interval", nullableString (interval))
        .set ("checkout_url", nullableString (checkoutUrl))
        .build();
}

std::optional<std::vector<PlanInfo>> PlanInfo::listFromJson (const juce::var& json)
{
    std::vector<PlanInfo> plans;

    if (! readObjectArray (json, "plans", plans, &PlanInfo::fromJson))
        return std::nullopt;

    return plans;
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
    const auto key = text.trim().toLowerCase();

    for (const auto state : { JobState::Queued, JobState::Running, JobState::Succeeded, JobState::Failed, JobState::Cancelled })
        if (toString (state) == key)
            return state;

    return std::nullopt;
}

std::optional<JobStage> jobStageFromString (const juce::String& text)
{
    const auto key = text.trim().toLowerCase();

    for (const auto stage : { JobStage::Upload, JobStage::Separate, JobStage::Transcribe,
                              JobStage::Analyze, JobStage::Package, JobStage::Done })
        if (toString (stage) == key)
            return stage;

    return std::nullopt;
}

std::optional<JobOptions> JobOptions::fromJson (const juce::var& json)
{
    if (! json.isObject())
        return std::nullopt;

    JobOptions options;

    if (! readOptionalInt (json, "client_sample_rate", options.clientSampleRate)
        || ! readStringArray (json, "stems", options.stems)
        || ! readStringArray (json, "transcribe", options.transcribe)
        || ! readBool (json, "drum_slices", options.drumSlices, false)
        || ! readInt (json, "target_root_midi", options.targetRootMidi, false)
        || ! readString (json, "idempotency_key", options.idempotencyKey, false))
        return std::nullopt;

    return options;
}

juce::var JobOptions::toVar() const
{
    ObjectBuilder builder;

    if (clientSampleRate.has_value())
        builder.set ("client_sample_rate", *clientSampleRate);

    if (! stems.isEmpty())
        builder.set ("stems", stringArrayToVar (stems));

    if (! transcribe.isEmpty())
        builder.set ("transcribe", stringArrayToVar (transcribe));

    builder.set ("drum_slices", drumSlices).set ("target_root_midi", targetRootMidi);

    if (idempotencyKey.isNotEmpty())
        builder.set ("idempotency_key", idempotencyKey);

    return builder.build();
}

juce::String JobOptions::toJsonString() const
{
    return juce::JSON::toString (toVar(), true);
}

std::optional<JobSubmitResponse> JobSubmitResponse::fromJson (const juce::var& json)
{
    JobSubmitResponse response;
    juce::String status;

    if (! readString (json, "job_id", response.jobId)
        || ! readString (json, "status", status, false)
        || ! readInt (json, "credits_reserved", response.creditsReserved, false)
        || ! readObject (json, "balance", response.balance, &CreditBalance::fromJson))
        return std::nullopt;

    if (status.isNotEmpty())
    {
        const auto parsed = jobStateFromString (status);

        if (! parsed.has_value())
            return std::nullopt;

        response.status = *parsed;
    }

    return response;
}

juce::var JobSubmitResponse::toVar() const
{
    return ObjectBuilder()
        .set ("job_id", jobId)
        .set ("status", toString (status))
        .set ("credits_reserved", creditsReserved)
        .set ("balance", balance.toVar())
        .build();
}

std::optional<InputInfo> InputInfo::fromJson (const juce::var& json)
{
    InputInfo info;

    if (! readDouble (json, "duration_seconds", info.durationSeconds)
        || ! readInt (json, "sample_rate", info.sampleRate)
        || ! readInt (json, "channels", info.channels)
        || ! readBool (json, "truncated", info.truncated))
        return std::nullopt;

    return info;
}

juce::var InputInfo::toVar() const
{
    return ObjectBuilder()
        .set ("duration_seconds", durationSeconds)
        .set ("sample_rate", sampleRate)
        .set ("channels", channels)
        .set ("truncated", truncated)
        .build();
}

std::optional<KeyInfo> KeyInfo::fromJson (const juce::var& json)
{
    KeyInfo info;

    if (! readString (json, "root", info.root)
        || ! readString (json, "mode", info.mode)
        || ! readInt (json, "root_midi", info.rootMidi)
        || ! readDouble (json, "confidence", info.confidence)
        || ! readIntArray (json, "scale_pitch_classes", info.scalePitchClasses))
        return std::nullopt;

    return info;
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
    return ObjectBuilder()
        .set ("root", root)
        .set ("mode", mode)
        .set ("root_midi", rootMidi)
        .set ("confidence", confidence)
        .set ("scale_pitch_classes", intArrayToVar (scalePitchClasses))
        .build();
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
    Analysis analysis;

    if (! readDouble (json, "bpm", analysis.bpm)
        || ! readDouble (json, "bpm_confidence", analysis.bpmConfidence)
        || ! readObject (json, "key", analysis.key, &KeyInfo::fromJson)
        || ! readDoubleArray (json, "downbeats_seconds", analysis.downbeatsSeconds)
        || ! readDoubleArray (json, "beats_seconds", analysis.beatsSeconds))
        return std::nullopt;

    return analysis;
}

juce::var Analysis::toVar() const
{
    return ObjectBuilder()
        .set ("bpm", bpm)
        .set ("bpm_confidence", bpmConfidence)
        .set ("key", key.toVar())
        .set ("downbeats_seconds", doubleArrayToVar (downbeatsSeconds))
        .set ("beats_seconds", doubleArrayToVar (beatsSeconds))
        .build();
}

std::optional<StemInfo> StemInfo::fromJson (const juce::var& json)
{
    StemInfo stem;

    if (! readString (json, "name", stem.name)
        || ! readString (json, "url", stem.url, false)
        || ! readString (json, "format", stem.format, false)
        || ! readInt (json, "sample_rate", stem.sampleRate)
        || ! readInt (json, "channels", stem.channels)
        || ! readDouble (json, "duration_seconds", stem.durationSeconds)
        || ! readInt (json, "root_midi", stem.rootMidi, false)
        || ! readDouble (json, "root_confidence", stem.rootConfidence, false)
        || ! readDouble (json, "peak_db", stem.peakDb)
        || ! readDouble (json, "rms_db", stem.rmsDb)
        || ! readDoubleArray (json, "transients_seconds", stem.transientsSeconds)
        || ! readOptionalObject (json, "suggested_adsr", stem.suggestedAdsr, &adsrFromJson)
        || ! readObjectArray (json, "slices", stem.slices, &sliceFromJson, false))
        return std::nullopt;

    return stem;
}

juce::var StemInfo::toVar() const
{
    ObjectBuilder builder;
    builder.set ("name", name)
           .set ("url", nullableString (url))
           .set ("format", format)
           .set ("sample_rate", sampleRate)
           .set ("channels", channels)
           .set ("duration_seconds", durationSeconds)
           .set ("root_midi", rootMidi)
           .set ("root_confidence", rootConfidence)
           .set ("peak_db", peakDb)
           .set ("rms_db", rmsDb)
           .set ("transients_seconds", doubleArrayToVar (transientsSeconds))
           .set ("suggested_adsr", suggestedAdsr.has_value() ? adsrToVar (*suggestedAdsr) : juce::var());

    if (! slices.empty())
        builder.set ("slices", arrayToVar (slices, sliceToVar));

    return builder.build();
}

std::optional<MidiInfo> MidiInfo::fromJson (const juce::var& json)
{
    MidiInfo midi;

    if (! readString (json, "url", midi.url, false)
        || ! readInt (json, "ppq", midi.ppq, false)
        || ! readDouble (json, "bpm", midi.bpm)
        || ! readObjectArray (json, "tracks", midi.tracks, &trackFromJson))
        return std::nullopt;

    return midi;
}

juce::var MidiInfo::toVar() const
{
    return ObjectBuilder()
        .set ("url", nullableString (url))
        .set ("ppq", ppq)
        .set ("bpm", bpm)
        .set ("tracks", arrayToVar (tracks, trackToVar))
        .build();
}

std::optional<JobResult> JobResult::fromJson (const juce::var& json)
{
    JobResult result;

    if (! readString (json, "job_id", result.jobId)
        || ! readInt (json, "credits_charged", result.creditsCharged)
        || ! readInt (json, "balance_after", result.balanceAfter)
        || ! readObject (json, "input", result.input, &InputInfo::fromJson)
        || ! readObject (json, "analysis", result.analysis, &Analysis::fromJson)
        || ! readObjectArray (json, "stems", result.stems, &StemInfo::fromJson)
        || ! readObject (json, "midi", result.midi, &MidiInfo::fromJson)
        || ! readString (json, "expires_at", result.expiresAt))
        return std::nullopt;

    return result;
}

juce::var JobResult::toVar() const
{
    return ObjectBuilder()
        .set ("job_id", jobId)
        .set ("credits_charged", creditsCharged)
        .set ("balance_after", balanceAfter)
        .set ("input", input.toVar())
        .set ("analysis", analysis.toVar())
        .set ("stems", arrayToVar (stems, [] (const StemInfo& stem) { return stem.toVar(); }))
        .set ("midi", midi.toVar())
        .set ("expires_at", expiresAt)
        .build();
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
    const auto expiry = parseRfc3339 (expiresAt);
    return expiry.has_value() && now >= *expiry;
}

std::optional<JobStatus> JobStatus::fromJson (const juce::var& json)
{
    JobStatus status;
    juce::String state, stage;

    if (! readString (json, "job_id", status.jobId)
        || ! readString (json, "status", state)
        || ! readString (json, "stage", stage)
        || ! readDouble (json, "progress", status.progress)
        || ! readString (json, "created_at", status.createdAt)
        || ! readString (json, "started_at", status.startedAt, false)
        || ! readString (json, "finished_at", status.finishedAt, false)
        || ! readOptionalObject (json, "error", status.error, &ApiError::fromJson)
        || ! readOptionalObject (json, "result", status.result, &JobResult::fromJson))
        return std::nullopt;

    const auto parsedState = jobStateFromString (state);
    const auto parsedStage = jobStageFromString (stage);

    if (! parsedState.has_value() || ! parsedStage.has_value())
        return std::nullopt;

    status.status = *parsedState;
    status.stage = *parsedStage;
    status.progress = juce::jlimit (0.0, 1.0, status.progress);
    return status;
}

juce::var JobStatus::toVar() const
{
    return ObjectBuilder()
        .set ("job_id", jobId)
        .set ("status", toString (status))
        .set ("stage", toString (stage))
        .set ("progress", progress)
        .set ("created_at", createdAt)
        .set ("started_at", nullableString (startedAt))
        .set ("finished_at", nullableString (finishedAt))
        .set ("error", error.has_value() ? errorBodyToVar (*error) : juce::var())
        .set ("result", result.has_value() ? result->toVar() : juce::var())
        .build();
}

std::optional<JobEvent> JobEvent::fromSse (const juce::String& eventName, const juce::var& data)
{
    JobEvent event;

    if (eventName == "progress")
    {
        juce::String stage;
        double progress = 0.0;

        if (! readString (data, "stage", stage) || ! readDouble (data, "progress", progress))
            return std::nullopt;

        const auto parsedStage = jobStageFromString (stage);

        if (! parsedStage.has_value())
            return std::nullopt;

        event.type = Type::Progress;
        event.stage = *parsedStage;
        event.progress = juce::jlimit (0.0, 1.0, progress);
        return event;
    }

    if (eventName == "result")
    {
        auto status = JobStatus::fromJson (data);

        if (! status.has_value())
            return std::nullopt;

        event.type = Type::Result;
        event.stage = status->stage;
        event.progress = status->progress;
        event.status = std::move (status);
        return event;
    }

    if (eventName == "error")
    {
        auto error = ApiError::fromJson (data);

        if (! error.has_value())
            return std::nullopt;

        event.type = Type::Error;
        event.error = std::move (error);
        return event;
    }

    return std::nullopt;
}

std::optional<ApiKeyInfo> ApiKeyInfo::fromJson (const juce::var& json)
{
    ApiKeyInfo info;

    if (! readString (json, "id", info.id)
        || ! readString (json, "name", info.name)
        || ! readString (json, "prefix", info.prefix)
        || ! readString (json, "key", info.key, false)
        || ! readString (json, "created_at", info.createdAt, false))
        return std::nullopt;

    return info;
}

juce::var ApiKeyInfo::toVar() const
{
    ObjectBuilder builder;
    builder.set ("id", id).set ("name", name).set ("prefix", prefix);

    if (key.isNotEmpty())
        builder.set ("key", key);

    builder.set ("created_at", createdAt);
    return builder.build();
}

//==============================================================================
std::optional<core::Adsr> adsrFromJson (const juce::var& json)
{
    core::Adsr adsr;

    if (! readDouble (json, "attack_ms", adsr.attackMs)
        || ! readDouble (json, "decay_ms", adsr.decayMs)
        || ! readDouble (json, "sustain", adsr.sustain)
        || ! readDouble (json, "release_ms", adsr.releaseMs))
        return std::nullopt;

    return adsr;
}

juce::var adsrToVar (const core::Adsr& adsr)
{
    return ObjectBuilder()
        .set ("attack_ms", adsr.attackMs)
        .set ("decay_ms", adsr.decayMs)
        .set ("sustain", adsr.sustain)
        .set ("release_ms", adsr.releaseMs)
        .build();
}

std::optional<core::Slice> sliceFromJson (const juce::var& json)
{
    core::Slice slice;

    if (! readDouble (json, "start_seconds", slice.startSeconds)
        || ! readDouble (json, "end_seconds", slice.endSeconds)
        || ! readInt (json, "midi_note", slice.midiNote))
        return std::nullopt;

    return slice;
}

juce::var sliceToVar (const core::Slice& slice)
{
    return ObjectBuilder()
        .set ("start_seconds", slice.startSeconds)
        .set ("end_seconds", slice.endSeconds)
        .set ("midi_note", slice.midiNote)
        .build();
}

std::optional<core::Note> noteFromJson (const juce::var& json)
{
    core::Note note;

    if (! readDouble (json, "start_seconds", note.startSeconds)
        || ! readDouble (json, "duration_seconds", note.durationSeconds)
        || ! readInt (json, "start_ticks", note.startTicks)
        || ! readInt (json, "duration_ticks", note.durationTicks)
        || ! readInt (json, "pitch", note.pitch)
        || ! readInt (json, "velocity", note.velocity))
        return std::nullopt;

    return note;
}

juce::var noteToVar (const core::Note& note)
{
    return ObjectBuilder()
        .set ("start_seconds", note.startSeconds)
        .set ("duration_seconds", note.durationSeconds)
        .set ("start_ticks", note.startTicks)
        .set ("duration_ticks", note.durationTicks)
        .set ("pitch", note.pitch)
        .set ("velocity", note.velocity)
        .build();
}

std::optional<core::Track> trackFromJson (const juce::var& json)
{
    core::Track track;
    juce::String name;

    if (! readString (json, "name", name)
        || ! readInt (json, "channel", track.channel)
        || ! readObjectArray (json, "notes", track.notes, &noteFromJson))
        return std::nullopt;

    track.name = name.toStdString();
    return track;
}

juce::var trackToVar (const core::Track& track)
{
    return ObjectBuilder()
        .set ("name", juce::String (track.name))
        .set ("channel", track.channel)
        .set ("notes", arrayToVar (track.notes, noteToVar))
        .build();
}

} // namespace snapplay::cloud
