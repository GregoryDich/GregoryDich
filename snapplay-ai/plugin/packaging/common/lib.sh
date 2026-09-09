# Shared helpers for the bash packaging scripts. Source it, do not execute it:
#
#   source "$(dirname "${BASH_SOURCE[0]}")/../common/lib.sh"
#
# Provides: PACKAGING_DIR, PLUGIN_DIR, REPO_DIR, BUILD_DIR, DIST_DIR, log/warn/die,
# run (DRY_RUN-aware), load_product_env, resolve_version, artefact path helpers.

set -euo pipefail

SCRIPT_NAME="$(basename "${BASH_SOURCE[1]:-${0}}")"
PACKAGING_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PLUGIN_DIR="$(cd "${PACKAGING_DIR}/.." && pwd)"
REPO_DIR="$(cd "${PLUGIN_DIR}/.." && pwd)"
BUILD_DIR="${BUILD_DIR:-${PLUGIN_DIR}/build}"
DIST_DIR="${DIST_DIR:-${PLUGIN_DIR}/dist}"
PYTHON="${PYTHON:-python3}"

log()  { printf '[%s] %s\n' "${SCRIPT_NAME}" "$*" >&2; }
warn() {
    log "WARNING: $*"
    [[ -n "${GITHUB_ACTIONS:-}" ]] && printf '::warning::%s\n' "$*"
    return 0
}
die() {
    log "ERROR: $*"
    [[ -n "${GITHUB_ACTIONS:-}" ]] && printf '::error::%s\n' "$*"
    exit 1
}

is_dry_run() { [[ "${DRY_RUN:-0}" == "1" ]]; }

# run CMD ARGS... - print the command, then execute it unless DRY_RUN=1.
run() {
    local shown
    shown="$(printf ' %q' "$@")"
    if is_dry_run; then
        printf '+ (dry-run)%s\n' "${shown}"
        return 0
    fi
    printf '+%s\n' "${shown}" >&2
    "$@"
}

# Same as run, but the first argument names an env var whose value must never be printed.
run_redacted() {
    local secret_var="$1"; shift
    local shown arg
    shown=""
    for arg in "$@"; do
        if [[ -n "${!secret_var:-}" && "${arg}" == "${!secret_var}" ]]; then
            shown+=" '<${secret_var}>'"
        else
            shown+=" $(printf '%q' "${arg}")"
        fi
    done
    if is_dry_run; then
        printf '+ (dry-run)%s\n' "${shown}"
        return 0
    fi
    printf '+%s\n' "${shown}" >&2
    "$@"
}

require_tool() {
    local tool
    for tool in "$@"; do
        if ! command -v "${tool}" >/dev/null 2>&1; then
            is_dry_run && { log "dry-run: '${tool}' is not installed here, continuing"; continue; }
            die "required tool '${tool}' not found in PATH"
        fi
    done
}

# Export everything in product.env and check the keys every script relies on.
load_product_env() {
    local env_file="${PACKAGING_DIR}/product.env" key
    [[ -f "${env_file}" ]] || die "missing ${env_file}"
    set -a
    # shellcheck source=../product.env
    source "${env_file}"
    set +a
    for key in PRODUCT_NAME PRODUCT_SLUG BUNDLE_ID_BASE VENDOR_NAME VENDOR_URL \
               PLUGIN_MANUFACTURER_CODE PLUGIN_CODE AU_TYPE AU_SUBTYPE AU_MANUFACTURER \
               MIN_MACOS COPYRIGHT_HOLDER CMAKE_TARGET CMAKE_OPTION_PREFIX; do
        [[ -n "${!key:-}" ]] || die "product.env: ${key} is empty"
    done
    [[ "${PRODUCT_SLUG}" =~ ^[A-Za-z0-9._-]+$ ]] || die "product.env: PRODUCT_SLUG may not contain spaces"
    [[ ${#PLUGIN_MANUFACTURER_CODE} -eq 4 && ${#PLUGIN_CODE} -eq 4 ]] || die "product.env: plugin codes must be 4 characters"
}

# Sets VERSION (as tagged, e.g. 1.2.3 or 1.2.3-rc1) and VERSION_NUMERIC (1.2.3, what CMake and
# installer metadata accept). Precedence: $1, $VERSION, the git tag of a tag build, then the
# default in CMakeLists.txt.
resolve_version() {
    local raw="${1:-${VERSION:-}}"
    if [[ -z "${raw}" && "${GITHUB_REF_TYPE:-}" == "tag" ]]; then
        raw="${GITHUB_REF_NAME}"
    fi
    if [[ -z "${raw}" ]]; then
        raw="$(sed -n "s/^set(${CMAKE_OPTION_PREFIX}_VERSION \"\([^\"]*\)\".*/\1/p" "${PLUGIN_DIR}/CMakeLists.txt" | head -n 1)"
        [[ -n "${raw}" ]] || die "no version given and CMakeLists.txt has no ${CMAKE_OPTION_PREFIX}_VERSION default"
        log "no version given, using CMakeLists.txt default ${raw}"
    fi
    raw="${raw#v}"
    [[ "${raw}" =~ ^([0-9]+\.[0-9]+\.[0-9]+)(-[0-9A-Za-z.]+)?$ ]] \
        || die "version '${raw}' is not X.Y.Z or X.Y.Z-prerelease"
    VERSION="${raw}"
    VERSION_NUMERIC="${BASH_REMATCH[1]}"
    export VERSION VERSION_NUMERIC
}

artefact_dir()      { printf '%s/%s_artefacts/Release' "${BUILD_DIR}" "${CMAKE_TARGET}"; }
vst3_bundle()       { printf '%s/VST3/%s.vst3' "$(artefact_dir)" "${PRODUCT_NAME}"; }
au_bundle()         { printf '%s/AU/%s.component' "$(artefact_dir)" "${PRODUCT_NAME}"; }
standalone_bundle() { printf '%s/Standalone/%s.app' "$(artefact_dir)" "${PRODUCT_NAME}"; }
bundle_binary()     { printf '%s/Contents/MacOS/%s' "$1" "${PRODUCT_NAME}"; }

# Writes the installer licence text: legal/eula.md rendered to plain text, or a placeholder
# (with a warning) when the EULA does not exist yet. See common/eula_to_txt.py for the flags.
write_license_text() {
    local out="$1"
    local -a flags=(--missing-ok)
    [[ "${ALLOW_LICENSE_PLACEHOLDER:-0}" == "1" ]] && flags+=(--unresolved-ok)
    run "${PYTHON}" "${PACKAGING_DIR}/common/eula_to_txt.py" "${REPO_DIR}/legal/eula.md" "${out}" "${flags[@]}"
}
