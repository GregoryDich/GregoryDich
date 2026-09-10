#!/usr/bin/env bash
# Install the built Audio Unit for the current user and run Apple's validator.
#
#   packaging/macos/auval.sh [path/to/Product.component]   (default: the build-tree AU)
#
# Fails unless auval prints "AU VALIDATION SUCCEEDED". AUVAL_STRICT=1 adds -strict.
# Passing auval is necessary for Logic Pro / GarageBand to list the plug-in, but Logic runs
# extra checks of its own - test there before a public release.

# shellcheck source=../common/lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/../common/lib.sh"

load_product_env
component="${1:-$(au_bundle)}"
is_dry_run || [[ -d "${component}" ]] || die "component not found: ${component}"
require_tool auval ditto

dest="${HOME}/Library/Audio/Plug-Ins/Components"
run mkdir -p "${dest}"
run rm -rf "${dest}/$(basename "${component}")"
run ditto "${component}" "${dest}/$(basename "${component}")"
# The registrar caches component lists; killing it forces a rescan (fails harmlessly when idle).
run killall -9 AudioComponentRegistrar || true

args=(-v "${AU_TYPE}" "${AU_SUBTYPE}" "${AU_MANUFACTURER}")
[[ "${AUVAL_STRICT:-0}" == "1" ]] && args=(-strict "${args[@]}")
if is_dry_run; then
    run auval "${args[@]}"
    exit 0
fi
set +e
output="$(auval "${args[@]}" 2>&1)"
status=$?
set -e
printf '%s\n' "${output}"
grep -q "AU VALIDATION SUCCEEDED" <<< "${output}" \
    || die "auval did not report AU VALIDATION SUCCEEDED (exit ${status})"
log "auval passed for ${AU_TYPE} ${AU_SUBTYPE} ${AU_MANUFACTURER}"
