#!/usr/bin/env bash
# Write a SHA-256 manifest (sha256sum -c compatible, base names only) for the release assets.
#
#   packaging/checksums.sh OUTPUT FILE...

source "$(dirname "${BASH_SOURCE[0]}")/common/lib.sh"

[[ $# -ge 2 ]] || die "usage: $0 OUTPUT FILE..."
out="$1"; shift

if command -v sha256sum >/dev/null 2>&1; then
    hasher=(sha256sum)
elif command -v shasum >/dev/null 2>&1; then
    hasher=(shasum -a 256)
else
    die "neither sha256sum nor shasum is available"
fi

if is_dry_run; then
    run "${hasher[@]}" "$@"
    printf '+ (dry-run) write %s\n' "${out}"
    exit 0
fi

: > "${out}"
for file in "$@"; do
    [[ -f "${file}" ]] || die "not a file: ${file}"
    (cd "$(dirname "${file}")" && "${hasher[@]}" "$(basename "${file}")") >> "${out}"
done
log "wrote ${out}:"
cat "${out}" >&2
