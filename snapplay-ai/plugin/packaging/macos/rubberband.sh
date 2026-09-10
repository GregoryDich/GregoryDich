#!/usr/bin/env bash
# Builds Rubber Band Library as a universal (arm64 + x86_64) static library and exports
# PKG_CONFIG_PATH so CMakeLists.txt's pkg_check_modules(rubberband) picks it up.
#
# Why not `brew install rubberband`: Homebrew ships a single-architecture dylib for the
# runner's own CPU. A universal plugin cannot link it, and a plugin bundle must not depend on
# /opt/homebrew/lib at all on a user's machine. The single-file build (vDSP FFT, built-in
# resampler) needs nothing but clang and the Accelerate framework JUCE already links.
#
# Source this file or run it; with MACOS_ARCHS and MIN_MACOS from the caller/product.env.
# Rubber Band is GPL-2.0-or-later OR commercial: a closed-source release needs the commercial
# licence (see research/legal notes) - this script only builds it.

# shellcheck source=../common/lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/../common/lib.sh"

RUBBERBAND_GIT="${RUBBERBAND_GIT:-https://github.com/breakfastquay/rubberband.git}"
RUBBERBAND_TAG="${RUBBERBAND_TAG:-v3.3.0}"
RUBBERBAND_COMMIT="${RUBBERBAND_COMMIT:-2be46b0dffb13273a67396c77bc9278736bb03d2}"
MACOS_ARCHS="${MACOS_ARCHS:-arm64;x86_64}"

build_rubberband() {
    local prefix="${BUILD_DIR}/rubberband" src obj arch_flags=() arch
    src="${prefix}/src"
    obj="${prefix}/RubberBandSingle.o"

    if [[ -f "${prefix}/lib/pkgconfig/rubberband.pc" && -f "${prefix}/lib/librubberband.a" ]]; then
        log "Rubber Band already built in ${prefix}"
    else
        require_tool git clang++ libtool
        run mkdir -p "${prefix}/lib/pkgconfig" "${prefix}/include"
        if [[ ! -d "${src}/.git" ]]; then
            run git clone --quiet --depth 1 --branch "${RUBBERBAND_TAG}" "${RUBBERBAND_GIT}" "${src}"
        fi
        if ! is_dry_run; then
            local head
            head="$(git -C "${src}" rev-parse HEAD)"
            [[ "${head}" == "${RUBBERBAND_COMMIT}" ]] \
                || die "Rubber Band ${RUBBERBAND_TAG} resolved to ${head}, expected ${RUBBERBAND_COMMIT}"
        fi
        IFS=';' read -r -a archs <<< "${MACOS_ARCHS}"
        for arch in "${archs[@]}"; do arch_flags+=(-arch "${arch}"); done
        run clang++ -std=c++17 -O3 -DNDEBUG -fPIC "${arch_flags[@]}" \
            -mmacosx-version-min="${MIN_MACOS}" \
            -c "${src}/single/RubberBandSingle.cpp" -o "${obj}"
        run libtool -static -o "${prefix}/lib/librubberband.a" "${obj}"
        run cp -R "${src}/rubberband" "${prefix}/include/"
        if ! is_dry_run; then
            cat > "${prefix}/lib/pkgconfig/rubberband.pc" <<PC
prefix=${prefix}
libdir=\${prefix}/lib
includedir=\${prefix}/include

Name: rubberband
Description: Rubber Band Library (static, single-file build)
Version: ${RUBBERBAND_TAG#v}
Libs: -L\${libdir} -lrubberband -framework Accelerate
Cflags: -I\${includedir}
PC
        else
            printf '+ (dry-run) write %s\n' "${prefix}/lib/pkgconfig/rubberband.pc"
        fi
    fi
    export PKG_CONFIG_PATH="${prefix}/lib/pkgconfig${PKG_CONFIG_PATH:+:${PKG_CONFIG_PATH}}"
    log "PKG_CONFIG_PATH=${PKG_CONFIG_PATH}"
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    load_product_env
    build_rubberband
fi
