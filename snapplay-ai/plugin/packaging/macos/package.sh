#!/usr/bin/env bash
# Build the flat installer package: one component pkg per format (pkgbuild), combined by
# productbuild with a "VST3" and an "Audio Unit" choice, signed with the Developer ID
# Installer certificate. Output: DIST_DIR/<PRODUCT_SLUG>-<VERSION>-macOS.pkg
# (…-macOS-unsigned.pkg when built without a certificate under ALLOW_UNSIGNED=1).
#
#   packaging/macos/package.sh [VERSION]
#
# Environment: DEVELOPER_ID_INSTALLER (auto-detected when unset), ALLOW_UNSIGNED=1 to build an
# unsigned pkg for dry runs, ALLOW_LICENSE_PLACEHOLDER=1 (dry runs: tolerate unresolved EULA
# tokens), BUILD_DIR, DIST_DIR, DRY_RUN=1. Placeholder tokens in legal/eula.md are filled
# from PRODUCT_NAME, COMPANY_LEGAL_NAME, ... in the environment (see common/eula_to_txt.py).

source "$(dirname "${BASH_SOURCE[0]}")/../common/lib.sh"

load_product_env
resolve_version "${1:-}"
export PRODUCT_NAME

work="${BUILD_DIR}/pkg"
resources="${work}/resources"
vst3="$(vst3_bundle)"
au="$(au_bundle)"

sign_args=()
suffix=""
if [[ -z "${DEVELOPER_ID_INSTALLER:-}" && "${ALLOW_UNSIGNED:-0}" != "1" ]] && is_dry_run; then
    DEVELOPER_ID_INSTALLER="Developer ID Installer: <auto-detected>"
elif [[ -z "${DEVELOPER_ID_INSTALLER:-}" ]] && ! is_dry_run; then
    matches="$(security find-identity -v 2>/dev/null | grep -F "Developer ID Installer:" | sed -E 's/^ *[0-9]+\) ([0-9A-F]+) "(.*)"$/\2/' || true)"
    if [[ -n "${matches}" ]]; then
        [[ "$(printf '%s\n' "${matches}" | wc -l | tr -d ' ')" == "1" ]] || die "several Developer ID Installer identities; set DEVELOPER_ID_INSTALLER"
        DEVELOPER_ID_INSTALLER="${matches}"
    fi
fi
if [[ -n "${DEVELOPER_ID_INSTALLER:-}" ]]; then
    sign_args=(--sign "${DEVELOPER_ID_INSTALLER}" --timestamp)
    log "installer identity: ${DEVELOPER_ID_INSTALLER}"
else
    [[ "${ALLOW_UNSIGNED:-0}" == "1" ]] \
        || die "no Developer ID Installer identity in the keychain (set ALLOW_UNSIGNED=1 only for a dry run)"
    warn "no Developer ID Installer certificate: building an UNSIGNED package (ALLOW_UNSIGNED=1)"
    suffix="-unsigned"
fi

out="${DIST_DIR}/${PRODUCT_SLUG}-${VERSION}-macOS${suffix}.pkg"
require_tool pkgbuild productbuild ditto
run rm -rf "${work}"
run mkdir -p "${work}/roots/vst3" "${work}/roots/au" "${work}/pkgs" "${resources}" "${DIST_DIR}"

# One component package per format. A hand-written component plist keeps the bundle from
# being "relocated" by Installer onto a stray copy found elsewhere (e.g. ~/Library) - the
# classic plugin-installer bug with pkgbuild --component.
component_pkg() {
    local name="$1" bundle="$2" location="$3" identifier="$4"
    local root="${work}/roots/${name}" plist="${work}/${name}-component.plist"
    is_dry_run || [[ -d "${bundle}" ]] || die "bundle not found: ${bundle}"
    run ditto "${bundle}" "${root}/$(basename "${bundle}")"
    if is_dry_run; then
        printf '+ (dry-run) write %s (BundleIsRelocatable=false)\n' "${plist}"
    else
        cat > "${plist}" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<array>
    <dict>
        <key>BundleIsRelocatable</key><false/>
        <key>BundleIsVersionChecked</key><false/>
        <key>BundleOverwriteAction</key><string>upgrade</string>
        <key>RootRelativeBundlePath</key><string>$(basename "${bundle}")</string>
    </dict>
</array>
</plist>
PLIST
    fi
    run pkgbuild --root "${root}" --component-plist "${plist}" \
        --install-location "${location}" \
        --identifier "${identifier}" --version "${VERSION_NUMERIC}" \
        "${work}/pkgs/${name}.pkg"
}

component_pkg vst3 "${vst3}" /Library/Audio/Plug-Ins/VST3       "${BUNDLE_ID_BASE}.vst3"
component_pkg au   "${au}"   /Library/Audio/Plug-Ins/Components "${BUNDLE_ID_BASE}.au"

write_license_text "${resources}/license.txt"

render_template() {
    # Replaces @TOKEN@ markers; product values never contain the sed delimiter '|'.
    sed -e "s|@PRODUCT_NAME@|${PRODUCT_NAME}|g" \
        -e "s|@VERSION@|${VERSION}|g" \
        -e "s|@VERSION_NUMERIC@|${VERSION_NUMERIC}|g" \
        -e "s|@BUNDLE_ID_BASE@|${BUNDLE_ID_BASE}|g" \
        -e "s|@MIN_MACOS@|${MIN_MACOS}|g" \
        -e "s|@VENDOR_URL@|${VENDOR_URL}|g" \
        -e "s|@VST3_PKG@|vst3.pkg|g" \
        -e "s|@AU_PKG@|au.pkg|g" "$1"
}
if is_dry_run; then
    printf '+ (dry-run) render %s -> %s\n' "${PACKAGING_DIR}/macos/distribution.xml.in" "${work}/distribution.xml"
    printf '+ (dry-run) render %s -> %s\n' "${PACKAGING_DIR}/macos/resources/welcome.txt.in" "${resources}/welcome.txt"
else
    render_template "${PACKAGING_DIR}/macos/distribution.xml.in" > "${work}/distribution.xml"
    render_template "${PACKAGING_DIR}/macos/resources/welcome.txt.in" > "${resources}/welcome.txt"
    grep -q "@[A-Z_]*@" "${work}/distribution.xml" && die "unrendered token left in distribution.xml"
fi

run productbuild --distribution "${work}/distribution.xml" \
    --package-path "${work}/pkgs" --resources "${resources}" \
    ${sign_args[@]+"${sign_args[@]}"} "${out}"

if [[ ${#sign_args[@]} -gt 0 ]]; then
    run pkgutil --check-signature "${out}"
fi
log "wrote ${out}"
[[ -n "${GITHUB_OUTPUT:-}" ]] && printf 'pkg=%s\n' "${out}" >> "${GITHUB_OUTPUT}"
exit 0
