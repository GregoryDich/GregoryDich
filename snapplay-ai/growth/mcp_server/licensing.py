"""Rights records: what establishes that a clip may become advertising.

Publishing a derivative of a recording nobody licensed is copyright infringement, so the
engine never assumes a clip is clear. Every provider produces a ``RightsRecord`` and
``process_clip`` refuses to spend a credit on a clip whose record is not ``cleared``.

Where a record comes from:

* **Local files** (the licensed folder and any other path) — a manifest the operator writes.
  Two equivalent formats, the per-file one winning when both exist:

  ``<clip>.license.json`` next to the audio file::

      {"title": "Night Loop", "license": "commissioned buy-out (ads + derivatives)",
       "attribution": "in-house", "permits_advertising": true,
       "evidence": "contracts/2026-03-night-loop.pdf"}

  ``licences.json`` (or ``licenses.json``) in the same folder, keyed by file name — either
  flat or under a ``"clips"`` key::

      {"clips": {"loop.wav": {"license": "CC BY 4.0", "attribution": "A — https://…"}}}

  The legacy ``<clip>.json`` sidecar is still read and counts as a manifest entry when it
  names a ``license``. An entry establishes rights when it names a non-empty ``license``,
  does not set ``permits_advertising: false`` and does not name a NonCommercial /
  NoDerivatives licence. A clip with no entry at all is ``unknown`` — it is not processed.
* **Free Music Archive** — the licence the API reports, kept only when
  ``license_allows_ads`` accepts it (CC0, public domain, CC BY, CC BY-SA).
* **URLs and anything else** — ``unknown``. The caller may attest to the rights explicitly
  (``license_attestation``); that is an affirmative act by the operator, never a default.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

RightsStatus = Literal["cleared", "unknown", "denied"]
UNKNOWN_LICENSE = "unknown"
FOLDER_MANIFEST_NAMES: tuple[str, ...] = ("licences.json", "licenses.json")
MANIFEST_SUFFIX = ".license.json"

_NON_COMMERCIAL = re.compile(r"non[- ]?commercial|\bNC\b|no[- ]?derivatives?|\bND\b", re.I)
_COMMERCIAL_OK = re.compile(r"CC0|public domain|attribution|\bBY\b", re.I)

_HOW_TO_CLEAR_LOCAL = (
    f"add an entry for the file to {FOLDER_MANIFEST_NAMES[0]} in its folder or write a "
    f"<clip>{MANIFEST_SUFFIX} sidecar naming the licence, or pass license_attestation"
)
_HOW_TO_CLEAR_REMOTE = (
    "list the clip through list_source_clips(source='free_music_archive'), which carries the "
    "FMA licence, or pass license_attestation naming the licence you hold"
)


def license_allows_ads(license_title: str | None) -> bool:
    """True for CC0 / public domain / CC BY / CC BY-SA; NC and ND variants are rejected."""
    if not license_title:
        return False
    if _NON_COMMERCIAL.search(license_title):
        return False
    return bool(_COMMERCIAL_OK.search(license_title))


def license_denies_ads(license_title: str | None) -> bool:
    """True for licences that visibly forbid advertising use (NonCommercial, NoDerivatives)."""
    return bool(license_title) and bool(_NON_COMMERCIAL.search(license_title or ""))


class RightsRecord(BaseModel):
    """What is known about a clip's advertising rights, and where that knowledge came from."""

    status: RightsStatus = "unknown"
    license: str = UNKNOWN_LICENSE
    attribution: str | None = None
    evidence: str = Field(description="Where the licence was read from")
    authority: str | None = Field(
        default=None, description="Who holds the right, for operator attestations"
    )
    reason: str | None = Field(default=None, description="Why an unknown/denied clip is refused")

    @property
    def cleared(self) -> bool:
        return self.status == "cleared"


class LicenseAttestation(BaseModel):
    """An operator's explicit declaration of rights the engine cannot see for itself."""

    model_config = ConfigDict(extra="forbid")

    license: str = Field(min_length=1, description="The licence or contract that grants the use")
    permits_advertising: bool = Field(
        description="Must be true: advertising and derivative use are covered"
    )
    authority: str = Field(
        min_length=1, description="Who granted it / where the evidence is kept (contract, invoice)"
    )
    attribution: str | None = Field(
        default=None, description="Credit line the caption must carry, when the licence needs one"
    )


class RightsNotEstablished(RuntimeError):
    """Refusal to process a clip whose advertising rights are not established."""

    MISSING = "a licence that permits advertising and derivative use"

    def __init__(self, ref: str, source: str, rights: RightsRecord, remedy: str) -> None:
        self.rights = rights
        self.detail: dict[str, Any] = {
            "code": "rights_not_established",
            "ref": ref,
            "source": source,
            "status": rights.status,
            "license": rights.license,
            "evidence": rights.evidence,
            "reason": rights.reason,
            "missing": self.MISSING,
            "remedy": remedy,
        }
        super().__init__(
            "rights not established for {ref} (source={source}, status={status}, "
            "licence={license!r}): {reason}. Missing: {missing}. To proceed: {remedy}.".format(
                **self.detail
            )
        )

    def details(self) -> dict[str, Any]:
        """The refusal as data: what was found, what is missing, and how to supply it."""
        return dict(self.detail)


def unknown_rights(evidence: str, reason: str) -> RightsRecord:
    return RightsRecord(
        status="unknown", license=UNKNOWN_LICENSE, evidence=evidence, reason=reason
    )


def _as_str_map(data: object) -> dict[str, Any]:
    return {str(k): v for k, v in data.items()} if isinstance(data, dict) else {}


def _load_json(path: Path) -> dict[str, Any]:
    try:
        return _as_str_map(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return {}


def read_folder_manifest(directory: Path) -> dict[str, dict[str, Any]]:
    """Read ``licences.json`` / ``licenses.json``; keys are file names or bare stems."""
    for name in FOLDER_MANIFEST_NAMES:
        path = directory / name
        if not path.is_file():
            continue
        data = _load_json(path)
        clips = data.get("clips") if isinstance(data.get("clips"), dict) else data
        entries = _as_str_map(clips).items()
        return {str(k): _as_str_map(v) for k, v in entries if isinstance(v, dict)}
    return {}


def manifest_entry(
    path: Path, folder_manifest: dict[str, dict[str, Any]] | None = None
) -> tuple[dict[str, Any], str] | None:
    """The manifest entry for a clip and where it was read from, or None when there is none."""
    sidecar = path.with_name(path.name + MANIFEST_SUFFIX)
    if sidecar.is_file():
        entry = _load_json(sidecar)
        if entry:
            return entry, sidecar.name
    legacy = path.with_suffix(".json")
    if legacy.is_file():
        entry = _load_json(legacy)
        if entry:
            return entry, legacy.name
    manifest = read_folder_manifest(path.parent) if folder_manifest is None else folder_manifest
    for key in (path.name, path.stem):
        if key in manifest:
            return manifest[key], f"{FOLDER_MANIFEST_NAMES[0]} entry {key!r}"
    return None


def rights_from_manifest(
    path: Path, folder_manifest: dict[str, dict[str, Any]] | None = None
) -> RightsRecord:
    """Resolve a local clip's rights from its manifest entry (see the module docstring)."""
    found = manifest_entry(path, folder_manifest)
    if found is None:
        return unknown_rights(
            evidence="no manifest entry",
            reason=(
                f"no licence is recorded for {path.name}: neither {path.name}{MANIFEST_SUFFIX} nor "
                f"an entry in {FOLDER_MANIFEST_NAMES[0]} exists"
            ),
        )
    entry, evidence = found
    license_text = str(entry.get("license") or "").strip()
    attribution = entry.get("attribution")
    attribution = str(attribution) if attribution else None
    if not license_text:
        return RightsRecord(
            status="unknown",
            license=UNKNOWN_LICENSE,
            attribution=attribution,
            evidence=evidence,
            reason=f"{evidence} carries no 'license' field",
        )
    if entry.get("permits_advertising") is False:
        return RightsRecord(
            status="denied",
            license=license_text,
            attribution=attribution,
            evidence=evidence,
            reason=f"{evidence} sets permits_advertising: false",
        )
    if license_denies_ads(license_text):
        return RightsRecord(
            status="denied",
            license=license_text,
            attribution=attribution,
            evidence=evidence,
            reason=(
                f"{license_text!r} is a NonCommercial or NoDerivatives licence, "
                "which does not cover advertising"
            ),
        )
    return RightsRecord(
        status="cleared", license=license_text, attribution=attribution, evidence=evidence
    )


def rights_from_fma(license_title: str | None, attribution: str | None) -> RightsRecord:
    """The licence the Free Music Archive reports for a track."""
    evidence = "free_music_archive license_title"
    if not license_title:
        return unknown_rights(evidence, "the FMA listing carries no license_title")
    if not license_allows_ads(license_title):
        return RightsRecord(
            status="denied",
            license=license_title,
            attribution=attribution,
            evidence=evidence,
            reason=f"{license_title!r} does not allow commercial and derivative use",
        )
    return RightsRecord(
        status="cleared", license=license_title, attribution=attribution, evidence=evidence
    )


def rights_from_attestation(attestation: LicenseAttestation) -> RightsRecord:
    """The operator's own declaration — an affirmative act, recorded as such."""
    evidence = f"operator attestation ({attestation.authority})"
    if not attestation.permits_advertising:
        return RightsRecord(
            status="denied",
            license=attestation.license,
            attribution=attestation.attribution,
            evidence=evidence,
            authority=attestation.authority,
            reason="the attestation sets permits_advertising: false",
        )
    return RightsRecord(
        status="cleared",
        license=attestation.license,
        attribution=attestation.attribution,
        evidence=evidence,
        authority=attestation.authority,
    )


def parse_attestation(
    data: dict[str, Any] | LicenseAttestation | None,
) -> LicenseAttestation | None:
    """Validate a caller-supplied attestation, naming the fields it is missing."""
    if data is None:
        return None
    if isinstance(data, LicenseAttestation):
        return data
    try:
        return LicenseAttestation.model_validate(data)
    except Exception as exc:
        raise ValueError(
            "license_attestation must be an object with 'license' (string), "
            "'permits_advertising' (true) and 'authority' (string), plus an optional "
            f"'attribution': {exc}"
        ) from exc


def resolve_rights(
    ref: str,
    source: str,
    *,
    declared_license: str | None = None,
    declared_attribution: str | None = None,
    attestation: LicenseAttestation | None = None,
) -> RightsRecord:
    """The rights record for a clip about to be processed.

    An attestation wins, because it is the operator saying they hold rights the engine cannot
    see. Otherwise local files are resolved from their manifest, Free Music Archive clips from
    the licence carried by the listing, and everything else stays unknown.
    """
    if attestation is not None:
        return rights_from_attestation(attestation)
    if source == "free_music_archive":
        return rights_from_fma(declared_license, declared_attribution)
    if ref.startswith(("http://", "https://")):
        return unknown_rights(
            evidence="none",
            reason=(
                f"{source} clips carry no licence the engine can verify; a URL is not evidence "
                "of a licence"
            ),
        )
    return rights_from_manifest(Path(ref))


def remedy_for(source: str, ref: str) -> str:
    return _HOW_TO_CLEAR_REMOTE if ref.startswith(("http://", "https://")) else _HOW_TO_CLEAR_LOCAL


def require_cleared(ref: str, source: str, rights: RightsRecord) -> RightsRecord:
    """Return the record when it clears the clip for advertising; refuse otherwise."""
    if not rights.cleared:
        raise RightsNotEstablished(ref, source, rights, remedy_for(source, ref))
    return rights


def attribution_line(rights: RightsRecord | None) -> str | None:
    """The credit line a caption must carry, when the licence asks for one."""
    if rights is None or not rights.attribution:
        return None
    return f"Audio: {rights.attribution} ({rights.license})"
