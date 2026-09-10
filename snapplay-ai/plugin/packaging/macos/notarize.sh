#!/usr/bin/env bash
# Notarize the installer package with notarytool, staple the ticket and prove Gatekeeper
# accepts the result.
#
#   packaging/macos/notarize.sh <path/to/package.pkg>
#
# Credentials (the API key is preferred; the Apple ID pair is the fallback):
#   NOTARY_KEY_ID, NOTARY_ISSUER_ID, NOTARY_KEY_P8   App Store Connect API key (.p8 contents)
#   NOTARY_APPLE_ID, NOTARY_PASSWORD, NOTARY_TEAM_ID Apple ID + app-specific password
# NOTARY_TIMEOUT (default 30m), DRY_RUN=1.

# shellcheck source=../common/lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/../common/lib.sh"

[[ $# -eq 1 ]] || die "usage: $0 <package.pkg>"
pkg="$1"
is_dry_run || [[ -f "${pkg}" ]] || die "package not found: ${pkg}"
require_tool xcrun spctl

tmp_dir="$(mktemp -d "${TMPDIR:-/tmp}/notarize.XXXXXX")"
cleanup() { rm -rf "${tmp_dir}"; }
trap cleanup EXIT

auth=()
if [[ -n "${NOTARY_KEY_ID:-}" && -n "${NOTARY_ISSUER_ID:-}" && -n "${NOTARY_KEY_P8:-}" ]]; then
    key_file="${tmp_dir}/AuthKey_${NOTARY_KEY_ID}.p8"
    if [[ -n "${GITHUB_ACTIONS:-}" ]]; then
        while IFS= read -r line; do [[ -n "${line}" ]] && printf '::add-mask::%s\n' "${line}"; done <<< "${NOTARY_KEY_P8}"
    fi
    (umask 077 && printf '%s\n' "${NOTARY_KEY_P8}" > "${key_file}")
    auth=(--key "${key_file}" --key-id "${NOTARY_KEY_ID}" --issuer "${NOTARY_ISSUER_ID}")
    log "authenticating with App Store Connect API key ${NOTARY_KEY_ID}"
elif [[ -n "${NOTARY_APPLE_ID:-}" && -n "${NOTARY_PASSWORD:-}" && -n "${NOTARY_TEAM_ID:-}" ]]; then
    auth=(--apple-id "${NOTARY_APPLE_ID}" --password "${NOTARY_PASSWORD}" --team-id "${NOTARY_TEAM_ID}")
    log "authenticating with Apple ID ${NOTARY_APPLE_ID} (team ${NOTARY_TEAM_ID})"
else
    die "no notarization credentials: set NOTARY_KEY_ID/NOTARY_ISSUER_ID/NOTARY_KEY_P8 or NOTARY_APPLE_ID/NOTARY_PASSWORD/NOTARY_TEAM_ID"
fi

submit_log="${tmp_dir}/submit.log"
if is_dry_run; then
    run_redacted NOTARY_PASSWORD xcrun notarytool submit "${pkg}" "${auth[@]}" --wait --timeout "${NOTARY_TIMEOUT:-30m}"
else
    set +e
    run_redacted NOTARY_PASSWORD xcrun notarytool submit "${pkg}" "${auth[@]}" --wait --timeout "${NOTARY_TIMEOUT:-30m}" | tee "${submit_log}"
    status=${PIPESTATUS[0]}
    set -e
    submission_id="$(awk '/^ *id: /{print $2; exit}' "${submit_log}")"
    if [[ ${status} -ne 0 ]] || ! grep -q "status: Accepted" "${submit_log}"; then
        log "notarization did not succeed (exit ${status}); fetching the log for ${submission_id:-<unknown id>}"
        if [[ -n "${submission_id}" ]]; then
            xcrun notarytool log "${submission_id}" "${auth[@]}" || true
        fi
        die "notarization failed"
    fi
    log "notarization accepted (submission ${submission_id})"
fi

run xcrun stapler staple "${pkg}"
run xcrun stapler validate "${pkg}"

if is_dry_run; then
    run spctl -a -vv -t install "${pkg}"
else
    assessment="$(spctl -a -vv -t install "${pkg}" 2>&1 || true)"
    printf '%s\n' "${assessment}"
    grep -q "accepted" <<< "${assessment}" || die "spctl did not accept ${pkg}"
    grep -q "source=Notarized Developer ID" <<< "${assessment}" || die "spctl: package is not recognised as Notarized Developer ID"
fi
log "${pkg} is notarized, stapled and accepted by Gatekeeper"
