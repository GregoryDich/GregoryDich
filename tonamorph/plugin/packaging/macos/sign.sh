#!/usr/bin/env bash
# Code-sign the built bundles with a Developer ID Application certificate and verify them.
#
#   packaging/macos/sign.sh [BUNDLE ...]      (default: the VST3 and AU from the build tree)
#
# Environment: DEVELOPER_ID_APPLICATION ("Developer ID Application: Name (TEAMID)" or its
# SHA-1; auto-detected from the keychain when unset), BUILD_DIR, BUILD_STANDALONE=1 to
# include the Standalone app, DRY_RUN=1.

# shellcheck source=../common/lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/../common/lib.sh"

load_product_env

find_identity() {
    # Prints the single valid identity of the requested kind, or fails.
    local kind="$1" matches
    matches="$(security find-identity -v 2>/dev/null | grep -F "${kind}:" | sed -E 's/^ *[0-9]+\) ([0-9A-F]+) "(.*)"$/\1 \2/' || true)"
    [[ -n "${matches}" ]] || die "no valid '${kind}' identity in the keychain; set the variable or import the certificate"
    [[ "$(printf '%s\n' "${matches}" | wc -l | tr -d ' ')" == "1" ]] \
        || die "several '${kind}' identities found; pick one via the environment variable:"$'\n'"${matches}"
    printf '%s' "${matches#* }"
}

if [[ -z "${DEVELOPER_ID_APPLICATION:-}" ]]; then
    if is_dry_run; then
        DEVELOPER_ID_APPLICATION="Developer ID Application: <auto-detected>"
    else
        DEVELOPER_ID_APPLICATION="$(find_identity "Developer ID Application")"
    fi
fi
log "signing identity: ${DEVELOPER_ID_APPLICATION}"

if [[ $# -gt 0 ]]; then
    bundles=("$@")
else
    bundles=("$(vst3_bundle)" "$(au_bundle)")
    [[ "${BUILD_STANDALONE:-0}" == "1" ]] && bundles+=("$(standalone_bundle)")
fi

require_tool codesign
for bundle in "${bundles[@]}"; do
    is_dry_run || [[ -d "${bundle}" ]] || die "bundle not found: ${bundle}"
    entitlements="${PACKAGING_DIR}/macos/entitlements.plist"
    [[ "${bundle}" == *.app ]] && entitlements="${PACKAGING_DIR}/macos/entitlements-standalone.plist"
    run codesign --force --deep --options runtime --timestamp \
        --entitlements "${entitlements}" \
        --sign "${DEVELOPER_ID_APPLICATION}" "${bundle}"
    run codesign --verify --deep --strict --verbose=2 "${bundle}"
    run codesign --display --verbose=2 "${bundle}"
done
log "signed ${#bundles[@]} bundle(s)"
