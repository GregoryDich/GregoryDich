"""pytest for eula_to_txt.py (stdlib only): python3 -m pytest plugin/packaging/common -q"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import eula_to_txt as mod  # noqa: E402

FIXTURE = """<!-- internal note: do not ship
spanning lines -->
# End User Licence Agreement

**Effective:** [[EFFECTIVE_DATE]] <!-- inline comment -->

This agreement is between you and [[COMPANY_LEGAL_NAME]] ("we") for [[PRODUCT_NAME]].

## 1. Grant

1. You may install *one* copy.
2. You may not `redistribute` it.

- Support: [[SUPPORT_EMAIL]]
- Site: [our site]([[WEBSITE_URL]])

| Plan | Credits |
|------|--------:|
| Free | 3 |
| Pro  | 100 |

---

> Copyright (c) [[EFFECTIVE_YEAR]] [[COMPANY_LEGAL_NAME]], [[COMPANY_ADDRESS]] (reg. [[COMPANY_REG_ID]]).
Questions: [[LEGAL_EMAIL]] / [[PRIVACY_EMAIL]]. Sold via [[MERCHANT_OF_RECORD]].
"""

VALUES = {
    "PRODUCT_NAME": "Example Plugin",
    "COMPANY_LEGAL_NAME": "Example Ltd",
    "COMPANY_ADDRESS": "1 Example Street",
    "COMPANY_REG_ID": "123456",
    "WEBSITE_URL": "https://example.test",
    "SUPPORT_EMAIL": "support@example.test",
    "PRIVACY_EMAIL": "privacy@example.test",
    "LEGAL_EMAIL": "legal@example.test",
    "MERCHANT_OF_RECORD": "Example MoR",
    "EFFECTIVE_DATE": "1 January 2030",
    "EFFECTIVE_YEAR": "2030",
}

EXPECTED = """END USER LICENCE AGREEMENT

Effective: 1 January 2030

This agreement is between you and Example Ltd ("we") for Example Plugin.

1. GRANT

- You may install one copy.
- You may not redistribute it.

- Support: support@example.test
- Site: our site (https://example.test)

Plan\tCredits
Free\t3
Pro\t100

Copyright (c) 2030 Example Ltd, 1 Example Street (reg. 123456).
Questions: legal@example.test / privacy@example.test. Sold via Example MoR.
"""


def test_convert_fixture() -> None:
    assert mod.convert(FIXTURE, VALUES) == EXPECTED


def test_comments_never_leak() -> None:
    text = mod.convert(FIXTURE, VALUES)
    assert "internal note" not in text
    assert "<!--" not in text and "-->" not in text


def test_unresolved_placeholder_raises_with_names() -> None:
    values = dict(VALUES)
    values["SUPPORT_EMAIL"] = ""
    del values["COMPANY_REG_ID"]
    with pytest.raises(mod.UnresolvedPlaceholderError) as info:
        mod.convert(FIXTURE, values)
    assert info.value.names == ("COMPANY_REG_ID", "SUPPORT_EMAIL")


def test_placeholder_names_cover_fixture() -> None:
    used = set(mod._PLACEHOLDER_RE.findall(FIXTURE))
    assert used == set(mod.PLACEHOLDER_NAMES)


def test_cli_converts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    for name, value in VALUES.items():
        monkeypatch.setenv(name, value)
    src = tmp_path / "eula.md"
    out = tmp_path / "out" / "license.txt"
    src.write_text(FIXTURE, encoding="utf-8")
    assert mod.main([str(src), str(out)]) == 0
    assert out.read_text(encoding="utf-8") == EXPECTED


def test_cli_fails_on_unresolved(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    for name in mod.PLACEHOLDER_NAMES:
        monkeypatch.delenv(name, raising=False)
    src = tmp_path / "eula.md"
    out = tmp_path / "license.txt"
    src.write_text(FIXTURE, encoding="utf-8")
    assert mod.main([str(src), str(out)]) == 2
    assert not out.exists()


def test_cli_unresolved_ok_writes_placeholder(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    for name in mod.PLACEHOLDER_NAMES:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("PRODUCT_NAME", "Example Plugin")
    src = tmp_path / "eula.md"
    out = tmp_path / "license.txt"
    src.write_text(FIXTURE, encoding="utf-8")
    assert mod.main([str(src), str(out), "--unresolved-ok"]) == 0
    text = out.read_text(encoding="utf-8")
    assert "PLACEHOLDER" in text and "MUST NOT BE DISTRIBUTED" in text
    assert "Example Plugin" in text
    assert "[[" not in text


def test_cli_missing_input(tmp_path: Path) -> None:
    out = tmp_path / "license.txt"
    assert mod.main([str(tmp_path / "absent.md"), str(out)]) == 3
    assert not out.exists()
    assert mod.main([str(tmp_path / "absent.md"), str(out), "--missing-ok"]) == 0
    assert "MUST NOT BE DISTRIBUTED" in out.read_text(encoding="utf-8")
