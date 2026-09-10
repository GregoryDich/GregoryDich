#!/usr/bin/env bash
# Configure and build the Release VST3 + AU (+ Standalone when BUILD_STANDALONE=1) as a
# universal binary for macOS >= MIN_MACOS.
#
#   packaging/macos/build.sh [VERSION]
#
# Environment: VERSION (else git tag, else CMakeLists default), BUILD_DIR (default plugin/build),
# MACOS_ARCHS (default "arm64;x86_64"), WITH_RUBBERBAND=1|0 (default 1, see rubberband.sh),
# BUILD_STANDALONE=1|0 (default 0), JOBS (default 4), DRY_RUN=1 to print the commands only.

source "$(dirname "${BASH_SOURCE[0]}")/../common/lib.sh"

load_product_env
resolve_version "${1:-}"
MACOS_ARCHS="${MACOS_ARCHS:-arm64;x86_64}"
WITH_RUBBERBAND="${WITH_RUBBERBAND:-1}"
BUILD_STANDALONE="${BUILD_STANDALONE:-0}"
JOBS="${JOBS:-4}"

require_tool cmake
log "${PRODUCT_NAME} ${VERSION} (numeric ${VERSION_NUMERIC}) archs=${MACOS_ARCHS} min macOS ${MIN_MACOS}"

use_rubberband=OFF
if [[ "${WITH_RUBBERBAND}" == "1" ]]; then
    require_tool pkg-config
    # shellcheck source=rubberband.sh
    source "${PACKAGING_DIR}/macos/rubberband.sh"
    build_rubberband
    use_rubberband=ON
fi

run cmake -S "${PLUGIN_DIR}" -B "${BUILD_DIR}" \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_OSX_ARCHITECTURES="${MACOS_ARCHS}" \
    -DCMAKE_OSX_DEPLOYMENT_TARGET="${MIN_MACOS}" \
    "-D${CMAKE_OPTION_PREFIX}_VERSION=${VERSION_NUMERIC}" \
    "-D${CMAKE_OPTION_PREFIX}_USE_RUBBERBAND=${use_rubberband}"

targets=("${CMAKE_TARGET}_VST3" "${CMAKE_TARGET}_AU")
[[ "${BUILD_STANDALONE}" == "1" ]] && targets+=("${CMAKE_TARGET}_Standalone")
for target in "${targets[@]}"; do
    run cmake --build "${BUILD_DIR}" --config Release --target "${target}" --parallel "${JOBS}"
done

if [[ "${WITH_RUBBERBAND}" == "1" ]] && ! is_dry_run; then
    grep -q "HAS_RUBBERBAND=1" "${BUILD_DIR}/CMakeCache.txt" 2>/dev/null \
        || grep -qs "Rubber Band .* found" "${BUILD_DIR}/CMakeFiles/CMakeOutput.log" 2>/dev/null \
        || warn "could not confirm from the CMake cache that Rubber Band was linked; check the configure log"
fi

bundles=("$(vst3_bundle)" "$(au_bundle)")
[[ "${BUILD_STANDALONE}" == "1" ]] && bundles+=("$(standalone_bundle)")
IFS=';' read -r -a wanted <<< "${MACOS_ARCHS}"
for bundle in "${bundles[@]}"; do
    if is_dry_run; then
        printf '+ (dry-run) expect %s\n' "${bundle}"
        continue
    fi
    [[ -d "${bundle}" ]] || die "expected bundle not found: ${bundle}"
    binary="$(bundle_binary "${bundle}")"
    [[ -f "${binary}" ]] || die "bundle has no Mach-O at ${binary}"
    archs="$(lipo -archs "${binary}")"
    for arch in "${wanted[@]}"; do
        [[ " ${archs} " == *" ${arch} "* ]] || die "${binary} lacks ${arch} (has: ${archs})"
    done
    log "built ${bundle} [${archs}]"
done
