#pragma once

/**
 * Every user-facing string of the plugin, in one place so the copy can be reviewed as a
 * whole (docs/GTM_PLAN.md, Appendix B §3). US English, at most twelve words per entry;
 * `{...}` placeholders are filled by the UI (see tonamorph::strings::fill).
 *
 * Standard-library only: the core tests iterate `table` to enforce the length rule and
 * scan the rest of Source/ for product-name literals that belong here instead.
 */

#include <cstddef>
#include <string>
#include <string_view>

namespace tonamorph::strings
{

/** The product name as shown to people; also the settings / cache folder name. */
inline constexpr const char* productName = "Tonamorph";

//==============================================================================
// Onboarding
inline constexpr const char* emptyDemo          = "Play a key. That's a morphed clip. Now drop yours.";
inline constexpr const char* dropZone           = "Drop any clip here. Up to 60 seconds.";
inline constexpr const char* dropAnother        = "Ready. Drop another clip to morph again.";
inline constexpr const char* signInToMorph      = "Sign in to morph your own clips. 3 free.";
inline constexpr const char* stageUploading     = "Uploading…";
inline constexpr const char* stageSeparating    = "Splitting bass, drums, synth, vocals…";
inline constexpr const char* stageTranscribing  = "Writing the MIDI…";
inline constexpr const char* stageAnalyzing     = "Finding the key and tempo…";
inline constexpr const char* stagePackaging     = "Almost there…";
inline constexpr const char* stageQueued        = "Waiting for an engine…";
inline constexpr const char* hintFirstSound     = "Ready. Play C3 — that's your bass, in key.";
inline constexpr const char* hintFirstDrag      = "Drag .mid into your piano roll.";
inline constexpr const char* truncated          = "Longer than 60 s — we morphed the first minute.";
inline constexpr const char* shakyKey           = "Key guess is shaky — tap to pick another.";
inline constexpr const char* cancelled          = "Cancelled. Morph returned.";
inline constexpr const char* ready              = "Ready.";

//==============================================================================
// Errors (contract §5 codes)
inline constexpr const char* errorTooLarge         = "That file's over 10 MB. Try a shorter or 16-bit clip.";
inline constexpr const char* errorUnsupported      = "That's not an audio file we can read. WAV, MP3, FLAC work.";
inline constexpr const char* errorRateLimited      = "Whoa, fast. Try again in a minute.";
inline constexpr const char* errorMaintenance      = "Morphing is paused for maintenance. Your morphs are safe.";
inline constexpr const char* errorWorkerBusy       = "Engine's busy. Nothing was charged — try again shortly.";
inline constexpr const char* errorMorphFailed      = "That morph didn't work. Morph returned. Try again?";
inline constexpr const char* errorOffline          = "You're offline. Loaded stems still play; morphing needs internet.";
inline constexpr const char* errorLostContact      = "Lost contact with the morph. Checking…";
inline constexpr const char* errorSignInAgain      = "Please sign in again.";
inline constexpr const char* errorWrongPassword    = "Wrong email or password.";
inline constexpr const char* errorUnconfirmedEmail = "Check your inbox to confirm, then sign in.";
inline constexpr const char* errorAuthRateLimited  = "Too many tries. Wait a minute, then sign in.";
inline constexpr const char* errorCacheMissing     = "Cached stems are missing. Morph again to play.";
inline constexpr const char* errorGeneric          = "Something went wrong. Try again?";
inline constexpr const char* errorNoCredits        = "No morphs left.";

//==============================================================================
// Paywall (GTM §2.4): exact state, equal buttons, no countdowns
inline constexpr const char* paywallHeadline         = "That was your last free morph. Nothing happens unless you buy.";
inline constexpr const char* paywallPackButton       = "{count} morphs · ${price} once";
inline constexpr const char* paywallSubscribeButton  = "{count} a month · ${price}/mo";
inline constexpr const char* paywallPackLine         = "Pack morphs never expire.";
inline constexpr const char* paywallSubscriptionLine = "Renews monthly. {count} morphs expire at period end. Cancel anytime.";
inline constexpr const char* notNow                  = "Not now";
inline constexpr int         paywallDefaultPackCredits = 50;
inline constexpr const char* paywallDefaultPackPrice   = "9";
inline constexpr int         paywallDefaultSubCredits  = 60;
inline constexpr const char* paywallDefaultSubPrice    = "7.99";

//==============================================================================
// Celebrations (visual only)
inline constexpr const char* celebrateFirstMorph    = "Your first morph. {key} · {bpm} BPM.";
inline constexpr const char* celebrateFirstDrag     = "MIDI's in your DAW.";
inline constexpr const char* celebrateFirstPurchase = "{count} morphs loaded. Thanks for backing a one-person shop.";

//==============================================================================
// Result feedback
inline constexpr const char* feedbackPrompt          = "How was this morph?";
inline constexpr const char* feedbackUp              = "Good";
inline constexpr const char* feedbackDown            = "Not good";
inline constexpr const char* feedbackReasonBleed     = "Stems bleed";
inline constexpr const char* feedbackReasonWrongKey  = "Wrong key";
inline constexpr const char* feedbackReasonMidiOff   = "MIDI is off";
inline constexpr const char* feedbackReasonClicks    = "Clicks";
inline constexpr const char* feedbackReasonSlow      = "Too slow";
inline constexpr const char* feedbackReasonOther     = "Other";
inline constexpr const char* feedbackNotePlaceholder = "Add a note (optional)";
inline constexpr const char* feedbackSend            = "Send";
inline constexpr const char* feedbackThanks          = "Thanks. That helps.";
inline constexpr const char* feedbackRefunded        = "Morph returned.";
inline constexpr const char* feedbackFailed          = "Couldn't send that. Try again?";

//==============================================================================
// Version banner
inline constexpr const char* updateAvailable = "{product} {version} is available.";
inline constexpr const char* updateRequired  = "Update required to keep morphing.";
inline constexpr const char* download        = "Download";
inline constexpr const char* dismiss         = "Dismiss";

//==============================================================================
// Sign-in and header
inline constexpr const char* signInTitle       = "Sign in to {product}";
inline constexpr const char* email             = "Email";
inline constexpr const char* emailPlaceholder  = "you@example.com";
inline constexpr const char* password          = "Password";
inline constexpr const char* signIn            = "Sign in";
inline constexpr const char* signingIn         = "Signing in…";
inline constexpr const char* createAccount     = "Create account";
inline constexpr const char* forgotPassword    = "Forgot password?";
inline constexpr const char* enterCredentials  = "Enter your email address and password.";
inline constexpr const char* logOut            = "Log out";
inline constexpr const char* credits           = "{count} morphs";
inline constexpr const char* creditsUnknown    = "— morphs";
inline constexpr const char* settings          = "Settings";
inline constexpr const char* crashReportsOptIn = "Send anonymous crash reports";

//==============================================================================
// Controls
inline constexpr const char* cancel          = "Cancel";
inline constexpr const char* dragMid         = "Drag .mid";
inline constexpr const char* dragFsc         = "Drag .fsc";
inline constexpr const char* chooseAudioFile = "Choose an audio file";
inline constexpr const char* saveMidiFile    = "Save MIDI file";
inline constexpr const char* saveFscFile     = "Save FL Studio score";
inline constexpr const char* savedFile       = "Saved {file}";
inline constexpr const char* couldNotWrite   = "Could not write {file}";
inline constexpr const char* scaleSnap       = "Scale-Snap";
inline constexpr const char* scaleRoot       = "Root";
inline constexpr const char* drumMode        = "Drum mode";
inline constexpr const char* bpmUnknown      = "— BPM";
inline constexpr const char* bpmValue        = "{bpm} BPM";
inline constexpr const char* keyUnknown      = "—";
inline constexpr const char* serviceUnreachable = "Could not reach the morph service.";

//==============================================================================
/** One row of the review table. */
struct Entry
{
    const char* id;
    const char* text;
};

inline constexpr Entry table[] = {
    { "productName", productName },
    { "emptyDemo", emptyDemo }, { "dropZone", dropZone }, { "dropAnother", dropAnother },
    { "signInToMorph", signInToMorph }, { "stageUploading", stageUploading },
    { "stageSeparating", stageSeparating }, { "stageTranscribing", stageTranscribing },
    { "stageAnalyzing", stageAnalyzing }, { "stagePackaging", stagePackaging }, { "stageQueued", stageQueued },
    { "hintFirstSound", hintFirstSound }, { "hintFirstDrag", hintFirstDrag }, { "truncated", truncated },
    { "shakyKey", shakyKey }, { "cancelled", cancelled }, { "ready", ready },
    { "errorTooLarge", errorTooLarge }, { "errorUnsupported", errorUnsupported },
    { "errorRateLimited", errorRateLimited }, { "errorMaintenance", errorMaintenance },
    { "errorWorkerBusy", errorWorkerBusy }, { "errorMorphFailed", errorMorphFailed },
    { "errorOffline", errorOffline }, { "errorLostContact", errorLostContact },
    { "errorSignInAgain", errorSignInAgain }, { "errorWrongPassword", errorWrongPassword },
    { "errorUnconfirmedEmail", errorUnconfirmedEmail }, { "errorAuthRateLimited", errorAuthRateLimited },
    { "errorCacheMissing", errorCacheMissing }, { "errorGeneric", errorGeneric }, { "errorNoCredits", errorNoCredits },
    { "paywallHeadline", paywallHeadline }, { "paywallPackButton", paywallPackButton },
    { "paywallSubscribeButton", paywallSubscribeButton }, { "paywallPackLine", paywallPackLine },
    { "paywallSubscriptionLine", paywallSubscriptionLine }, { "notNow", notNow },
    { "celebrateFirstMorph", celebrateFirstMorph }, { "celebrateFirstDrag", celebrateFirstDrag },
    { "celebrateFirstPurchase", celebrateFirstPurchase },
    { "feedbackPrompt", feedbackPrompt }, { "feedbackUp", feedbackUp }, { "feedbackDown", feedbackDown },
    { "feedbackReasonBleed", feedbackReasonBleed }, { "feedbackReasonWrongKey", feedbackReasonWrongKey },
    { "feedbackReasonMidiOff", feedbackReasonMidiOff }, { "feedbackReasonClicks", feedbackReasonClicks },
    { "feedbackReasonSlow", feedbackReasonSlow }, { "feedbackReasonOther", feedbackReasonOther },
    { "feedbackNotePlaceholder", feedbackNotePlaceholder }, { "feedbackSend", feedbackSend },
    { "feedbackThanks", feedbackThanks }, { "feedbackRefunded", feedbackRefunded }, { "feedbackFailed", feedbackFailed },
    { "updateAvailable", updateAvailable }, { "updateRequired", updateRequired },
    { "download", download }, { "dismiss", dismiss },
    { "signInTitle", signInTitle }, { "email", email }, { "emailPlaceholder", emailPlaceholder },
    { "password", password }, { "signIn", signIn }, { "signingIn", signingIn },
    { "createAccount", createAccount }, { "forgotPassword", forgotPassword },
    { "enterCredentials", enterCredentials }, { "logOut", logOut }, { "credits", credits },
    { "creditsUnknown", creditsUnknown }, { "settings", settings }, { "crashReportsOptIn", crashReportsOptIn },
    { "cancel", cancel }, { "dragMid", dragMid }, { "dragFsc", dragFsc },
    { "chooseAudioFile", chooseAudioFile }, { "saveMidiFile", saveMidiFile }, { "saveFscFile", saveFscFile },
    { "savedFile", savedFile }, { "couldNotWrite", couldNotWrite }, { "scaleSnap", scaleSnap },
    { "scaleRoot", scaleRoot }, { "drumMode", drumMode }, { "bpmUnknown", bpmUnknown }, { "bpmValue", bpmValue },
    { "keyUnknown", keyUnknown }, { "serviceUnreachable", serviceUnreachable },
};

inline constexpr std::size_t tableSize = sizeof (table) / sizeof (table[0]);

/** The maximum number of words any entry may have (GTM §2.4). */
inline constexpr int maxWordsPerString = 12;

/** Counts whitespace-separated tokens containing at least one letter or digit, so
    punctuation-only tokens such as a dash or a middle dot do not count as words. */
inline int countWords (std::string_view text) noexcept
{
    int words = 0;
    bool inToken = false;
    bool tokenHasWordChar = false;

    auto isSpace = [] (unsigned char c) { return c == ' ' || c == '\t' || c == '\n' || c == '\r'; };
    auto isWordChar = [] (unsigned char c)
    {
        return (c >= '0' && c <= '9') || (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || c == '{';
    };

    for (const char ch : text)
    {
        const auto c = static_cast<unsigned char> (ch);

        if (isSpace (c))
        {
            if (inToken && tokenHasWordChar)
                ++words;

            inToken = false;
            tokenHasWordChar = false;
            continue;
        }

        inToken = true;
        tokenHasWordChar = tokenHasWordChar || isWordChar (c);
    }

    if (inToken && tokenHasWordChar)
        ++words;

    return words;
}

/** Replaces every `{placeholder}` occurrence in `text` with `value`. */
inline std::string fill (std::string_view text, std::string_view placeholder, std::string_view value)
{
    std::string result (text);
    const std::string token = "{" + std::string (placeholder) + "}";

    for (auto pos = result.find (token); pos != std::string::npos; pos = result.find (token, pos + value.size()))
        result.replace (pos, token.size(), value);

    return result;
}

} // namespace tonamorph::strings
