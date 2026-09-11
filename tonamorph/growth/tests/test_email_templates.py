"""The Klaviyo templates under ``growth/email`` pass their checker, the checker rejects the
mistakes it exists to catch, and the manifest's variables exist in the backend."""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

EMAIL_DIR = Path(__file__).resolve().parents[1] / "email"
BUILD = EMAIL_DIR / "build.py"
MANIFEST = EMAIL_DIR / "manifest.json"
REPO = EMAIL_DIR.parents[1]
GROWTH_HOOKS = REPO / "backend" / "app" / "services" / "growth.py"
KLAVIYO_SERVICE = REPO / "backend" / "app" / "services" / "klaviyo.py"
SCHEMA = REPO / "db" / "migrations" / "0001_schema.sql"
UTM = "utm_source=klaviyo&utm_medium=email&utm_campaign="
# Emitted by the website, not the backend (contract section 14): the backend owns the name only.
WEBSITE_METRICS = frozenset({"Checkout Started"})


def load_checker() -> ModuleType:
    """``growth/email`` is deliberately not a package (as one it would shadow the standard
    library's ``email`` on ``pythonpath = ["."]``), so the script is loaded by path."""
    spec = importlib.util.spec_from_file_location("tonamorph_email_build", BUILD)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses resolve annotations through sys.modules
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module


@pytest.fixture(scope="module")
def checker() -> ModuleType:
    return load_checker()


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    """A private copy of the templates and manifest that a test may break."""
    root = tmp_path / "email"
    shutil.copytree(EMAIL_DIR, root)
    return root


def test_cli_check_passes() -> None:
    result = subprocess.run(
        [sys.executable, str(BUILD), "--check"], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "0 problems" in result.stdout


def test_checker_reports_every_template_ok(checker: ModuleType) -> None:
    report = checker.check(MANIFEST)
    assert report.problems == []
    assert [row["status"] for row in report.rows] == ["OK"] * 10


def test_marketing_template_needs_unsubscribe_and_known_variables(
    checker: ModuleType, workspace: Path
) -> None:
    page = workspace / "templates" / "welcome-0h.html"
    html = page.read_text(encoding="utf-8")
    broken = html.replace("{% unsubscribe 'Unsubscribe' %}", "").replace(
        "Reply if anything sticks.", "Reply if anything sticks, {{ event.nope }}. TonaMorph"
    )
    assert broken != html
    page.write_text(broken, encoding="utf-8")
    joined = "\n".join(checker.check(workspace / "manifest.json").problems)
    assert "welcome-0h: html: marketing template without {% unsubscribe %}" in joined
    assert "event.nope is not a property of metric 'Signed Up'" in joined
    assert "product name written as 'TonaMorph'" in joined


def test_transactional_template_rejects_marketing_content(
    checker: ModuleType, workspace: Path
) -> None:
    page = workspace / "templates" / "purchase-thank-you.html"
    html = page.read_text(encoding="utf-8")
    link = (
        f'<a href="https://tonamorph.com/pricing?{UTM}purchase&utm_content=purchase-thank-you">'
        "Buy more</a> "
    )
    page.write_text(html.replace("Thanks for backing", link + "Thanks for backing"), "utf-8")
    problems = checker.check(workspace / "manifest.json").problems
    assert any(p.startswith("purchase-thank-you:") and "/pricing" in p for p in problems)


def test_unbalanced_html_and_untagged_link_are_reported(
    checker: ModuleType, workspace: Path
) -> None:
    page = workspace / "templates" / "day-7-nudge.html"
    html = page.read_text(encoding="utf-8")
    tagged = f"https://tonamorph.com/download?{UTM}day-7&utm_content=day-7-nudge"
    assert tagged in html
    page.write_text(
        html.replace("</body>", "").replace(tagged, "https://tonamorph.com/download", 1),
        encoding="utf-8",
    )
    problems = checker.check(workspace / "manifest.json").problems
    assert any(p.startswith("day-7-nudge:") and "closes <body>" in p for p in problems)
    assert any(p.startswith("day-7-nudge:") and "link without utm_source" in p for p in problems)


def test_manifest_variables_exist_in_backend(checker: ModuleType) -> None:
    if not (GROWTH_HOOKS.is_file() and KLAVIYO_SERVICE.is_file() and SCHEMA.is_file()):
        pytest.skip("the backend is not part of this checkout")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    hooks = GROWTH_HOOKS.read_text(encoding="utf-8")
    schema = SCHEMA.read_text(encoding="utf-8")
    constants = set(checker.BACKEND_CONSTANT.findall(KLAVIYO_SERVICE.read_text("utf-8")))
    assert set(manifest["metrics"]) <= constants
    for metric, properties in manifest["metrics"].items():
        if metric in WEBSITE_METRICS:
            continue
        for prop in properties:
            if prop.startswith("checkout_url_"):
                # growth.py builds these as f"checkout_url_{plan.id}" over the paid plans.
                assert 'f"checkout_url_{plan.id}"' in hooks
                assert f"'{prop.removeprefix('checkout_url_')}'" in schema, (metric, prop)
            else:
                assert f'"{prop}"' in hooks, (metric, prop)
    for prop in manifest["profile_properties"]:
        assert f'"{prop}"' in hooks, prop
