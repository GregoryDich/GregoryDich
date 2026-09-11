#!/usr/bin/env python3
"""Checker for the Klaviyo email templates in this directory (standard library only).

``manifest.json`` is the single source of truth: which templates exist, which flow step
and trigger metric each serves, and which event and profile variables it may reference.
For every template listed there the checker verifies that

* the HTML parses with balanced tags (``html.parser``) and the ``.txt`` sibling exists;
* every ``{{ ... }}`` and ``{% ... %}`` token is on the allow-list the manifest derives:
  ``event.<property>`` only from the trigger metric's properties, ``person|lookup:'<p>'``
  only from the declared profile properties, the organization fields, the unsubscribe tag
  and ``if`` / ``elif`` / ``else`` / ``endif``; the manifest's own variable lists must equal
  what the files use, so a later MCP run can validate metrics before building flows;
* marketing templates carry ``{% unsubscribe %}`` (HTML) and ``{{ unsubscribe_link }}``
  (text); transactional templates carry neither and no checkout or pricing link;
* every link is UTM-tagged with the template's campaign, both versions link to the same
  URLs, and ``<title>`` and the preheader equal the manifest's subject and preview text;
* the product name appears only as the literal ``Tonamorph``. Email is the one place in
  the repository where that literal is allowed (GoTrue and Klaviyo have no variable for
  it, see README.md); the check catches re-cased or misspelt variants, not the name.

Nothing is inlined or rewritten: Klaviyo inlines the CSS itself when it sends.

    python3 growth/email/build.py            # summary table, exit 0
    python3 growth/email/build.py --check    # summary table, exit 1 on any problem
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
DEFAULT_MANIFEST = HERE / "manifest.json"
BACKEND_METRICS = HERE.parents[1] / "backend" / "app" / "services" / "klaviyo.py"
PRODUCT_NAME = "Tonamorph"

VOID_ELEMENTS = frozenset(
    {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source",
     "track", "wbr"}
)
TOKEN = re.compile(r"\{\{\s*(.*?)\s*\}\}|\{%\s*(.*?)\s*%\}", re.DOTALL)
VARIABLE = re.compile(
    r"^([A-Za-z_][\w.]*)((?:\|[a-z_]+(?::(?:'[^']*'|\"[^\"]*\"|[\w.-]+))?)*)$"
)
FILTER = re.compile(r"\|([a-z_]+)(?::('[^']*'|\"[^\"]*\"|[\w.-]+))?")
URL = re.compile(r"https?://[^\s'\"<>{}%()]+")
DOMAIN = re.compile(r"\btonamorph\.(?:com|lemonsqueezy\.com)\b", re.IGNORECASE)
BRAND_VARIANT = re.compile(r"tona\s*-?\s*m[o0]r(?:ph|f)\w*", re.IGNORECASE)
CHECKOUT_LINK = re.compile(
    r"\{\{\s*event\.(checkout_url_\w+)\s*\}\}"
    r"(?:&utm_source=klaviyo&utm_medium=email&utm_campaign=([\w-]+))?"
)
CONDITION_OPERATORS = frozenset({"==", "!=", "<", ">", "<=", ">=", "and", "or", "not", "in"})
LITERAL = re.compile(r"^(?:'[^']*'|\"[^\"]*\"|-?\d+(?:\.\d+)?|True|False|None)$")
HTML_TAG = re.compile(r"<[A-Za-z/!]")
BACKEND_CONSTANT = re.compile(r'^[A-Z_]+ = "([^"]+)"$', re.MULTILINE)
MARKETING_PATHS = ("/pricing", "/checkout", "checkout_url")


class TemplateParser(HTMLParser):
    """Collects tag-balance errors, link targets, text, ``<title>`` and the preheader."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[str] = []
        self.errors: list[str] = []
        self.hrefs: list[str] = []
        self.text: list[str] = []
        self.title = ""
        self.preheader = ""
        self._capture: str | None = None
        self._preheader_depth = -1

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "a":
            self.hrefs.append(attributes.get("href") or "")
        if tag == "title":
            self._capture = "title"
        elif "preheader" in (attributes.get("class") or "").split():
            self._capture = "preheader"
            self._preheader_depth = len(self.stack)
        if tag not in VOID_ELEMENTS:
            self.stack.append(tag)

    def handle_endtag(self, tag: str) -> None:
        if tag in VOID_ELEMENTS:
            return
        if not self.stack or self.stack[-1] != tag:
            line, _ = self.getpos()
            expected = self.stack[-1] if self.stack else "nothing"
            self.errors.append(f"line {line}: </{tag}> closes <{expected}>")
            return
        self.stack.pop()
        preheader_closed = (
            self._capture == "preheader" and len(self.stack) == self._preheader_depth
        )
        if tag == "title" or preheader_closed:
            self._capture = None

    def handle_data(self, data: str) -> None:
        if self._capture == "title":
            self.title += data
        elif self._capture == "preheader":
            self.preheader += data
        self.text.append(data)


@dataclass
class Usage:
    """What one file references."""

    event: set[str] = field(default_factory=set)
    profile: set[str] = field(default_factory=set)
    globals: set[str] = field(default_factory=set)
    unsubscribe_tag: bool = False


@dataclass
class Report:
    rows: list[dict[str, Any]] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)
    backend_checked: bool = False

    def problem(self, slug: str, message: str) -> None:
        self.problems.append(f"{slug}: {message}")

    def problems_for(self, slug: str) -> int:
        return sum(1 for problem in self.problems if problem.startswith(f"{slug}: "))


class Checker:
    def __init__(self, manifest: dict[str, Any], root: Path) -> None:
        self.manifest = manifest
        self.root = root
        self.metrics: dict[str, list[str]] = manifest["metrics"]
        self.profile_properties = set(manifest["profile_properties"])
        self.globals = set(manifest["globals"])
        self.tags = set(manifest["tags"])
        self.filters = set(manifest["filters"])
        self.report = Report()

    # --- manifest ------------------------------------------------------------------------

    def check_manifest(self) -> None:
        report = self.report
        seen: set[str] = set()
        for template in self.manifest["templates"]:
            slug = template["slug"]
            if slug in seen:
                report.problem(slug, "duplicate slug in the manifest")
            seen.add(slug)
            metric = template["trigger_metric"]
            if metric is not None and metric not in self.metrics:
                report.problem(slug, f"trigger metric {metric!r} is not in manifest.metrics")
            allowed = set(self.metrics.get(metric, [])) if metric else set()
            for variable in template["event_variables"]:
                if variable not in allowed:
                    report.problem(
                        slug, f"manifest lists event.{variable}, not a property of {metric!r}"
                    )
            for variable in template["profile_variables"]:
                if variable not in self.profile_properties:
                    report.problem(slug, f"manifest lists unknown profile property {variable}")
        if BACKEND_METRICS.exists():
            names = set(BACKEND_CONSTANT.findall(BACKEND_METRICS.read_text(encoding="utf-8")))
            for metric in self.metrics:
                if metric not in names:
                    report.problem("manifest", f"metric {metric!r} is not defined by the backend")
            report.backend_checked = True

    # --- one template ----------------------------------------------------------------------

    def check_template(self, template: dict[str, Any]) -> None:
        report = self.report
        slug = template["slug"]
        html_path = self.root / template["file"]
        text_path = self.root / template["text_file"]
        for path in (html_path, text_path):
            if not path.is_file():
                report.problem(slug, f"missing file {path.name}")
        if not (html_path.is_file() and text_path.is_file()):
            self.add_row(template)
            return
        html = html_path.read_text(encoding="utf-8")
        text = text_path.read_text(encoding="utf-8")

        parser = TemplateParser()
        parser.feed(html)
        parser.close()
        for error in parser.errors:
            report.problem(slug, error)
        if parser.stack:
            report.problem(slug, "unclosed <" + ">, <".join(parser.stack) + ">")
        if parser.title.strip() != template["subject"]:
            report.problem(slug, f"<title> {parser.title.strip()!r} is not the manifest subject")
        if parser.preheader.strip() != template["preview_text"]:
            report.problem(slug, "preheader text is not the manifest preview text")

        html_usage = self.check_tokens(template, html, "html")
        text_usage = self.check_tokens(template, text, "txt")
        event_used = html_usage.event | text_usage.event
        profile_used = html_usage.profile | text_usage.profile
        if event_used != set(template["event_variables"]):
            report.problem(
                slug,
                f"event variables used {sorted(event_used)} differ from the manifest "
                f"{sorted(template['event_variables'])}",
            )
        if profile_used != set(template["profile_variables"]):
            report.problem(
                slug,
                f"profile variables used {sorted(profile_used)} differ from the manifest "
                f"{sorted(template['profile_variables'])}",
            )

        text_unsubscribe = "unsubscribe_link" in text_usage.globals
        if template["transactional"]:
            if html_usage.unsubscribe_tag or text_unsubscribe:
                report.problem(slug, "transactional template carries an unsubscribe link")
            for variable in sorted(event_used):
                if variable.startswith("checkout_url_"):
                    report.problem(slug, f"transactional template uses event.{variable}")
            for href in parser.hrefs:
                if any(marker in href for marker in MARKETING_PATHS):
                    report.problem(slug, f"transactional template links to {href}")
        else:
            if not html_usage.unsubscribe_tag:
                report.problem(slug, "html: marketing template without {% unsubscribe %}")
            if not text_unsubscribe:
                report.problem(slug, "txt: marketing template without {{ unsubscribe_link }}")

        self.check_links(template, parser.hrefs, html, text)
        if "first_name" in html or "first_name" in text:
            report.problem(slug, "first_name is referenced; names are not collected")
        if HTML_TAG.search(text):
            report.problem(slug, "txt: contains HTML")
        self.check_brand(slug, "html", "".join(parser.text))
        self.check_brand(slug, "txt", text)
        self.add_row(template)

    def check_tokens(self, template: dict[str, Any], body: str, where: str) -> Usage:
        report = self.report
        slug = template["slug"]
        usage = Usage()
        depth = 0
        for match in TOKEN.finditer(body):
            variable, tag = match.group(1), match.group(2)
            if variable is not None:
                self.check_variable(template, variable, where, usage)
                continue
            words = tag.split()
            name = words[0] if words else ""
            if name not in self.tags:
                report.problem(slug, f"{where}: unknown tag {{% {tag} %}}")
            elif name == "unsubscribe":
                usage.unsubscribe_tag = True
                if len(words) > 1 and not LITERAL.match(" ".join(words[1:])):
                    report.problem(slug, f"{where}: unsubscribe label must be a quoted string")
            elif name in ("if", "elif"):
                if name == "if":
                    depth += 1
                elif depth == 0:
                    report.problem(slug, f"{where}: elif outside an if block")
                for operand in words[1:]:
                    if operand in CONDITION_OPERATORS or LITERAL.match(operand):
                        continue
                    self.check_variable(template, operand, where, usage)
            elif name == "else":
                if depth == 0:
                    report.problem(slug, f"{where}: else outside an if block")
            elif name == "endif":
                depth -= 1
                if depth < 0:
                    report.problem(slug, f"{where}: endif without if")
                    depth = 0
        if depth:
            report.problem(slug, f"{where}: if without endif")
        return usage

    def check_variable(
        self, template: dict[str, Any], expression: str, where: str, usage: Usage
    ) -> None:
        report = self.report
        slug = template["slug"]
        match = VARIABLE.match(expression)
        if match is None:
            report.problem(slug, f"{where}: cannot parse {{{{ {expression} }}}}")
            return
        base, filters_text = match.group(1), match.group(2)
        filters = FILTER.findall(filters_text)
        for name, _ in filters:
            if name not in self.filters:
                report.problem(slug, f"{where}: filter {name!r} is not allowed")
        lookups = [index for index, (name, _) in enumerate(filters) if name == "lookup"]
        if base == "person":
            if lookups != [0]:
                report.problem(slug, f"{where}: person must be person|lookup:'property'")
                return
            prop = filters[0][1].strip("'\"")
            if prop not in self.profile_properties:
                report.problem(slug, f"{where}: unknown profile property {prop!r}")
            usage.profile.add(prop)
            return
        if lookups:
            report.problem(slug, f"{where}: lookup is only valid directly after person")
        if base.startswith("person."):
            report.problem(
                slug, f"{where}: {base} is a profile attribute we do not collect; use lookup"
            )
        elif base.startswith("event."):
            prop = base[len("event.") :]
            metric = template["trigger_metric"]
            allowed = self.metrics.get(metric, []) if metric else []
            if prop not in allowed:
                report.problem(slug, f"{where}: {base} is not a property of metric {metric!r}")
            usage.event.add(prop)
        elif base in self.globals:
            usage.globals.add(base)
        else:
            report.problem(slug, f"{where}: {base} is not an allowed variable")

    def check_links(
        self, template: dict[str, Any], hrefs: list[str], html: str, text: str
    ) -> None:
        report = self.report
        slug = template["slug"]
        needle = f"utm_source=klaviyo&utm_medium=email&utm_campaign={template['utm_campaign']}"
        html_urls: set[str] = set()
        for href in hrefs:
            if not href:
                report.problem(slug, "html: <a> without href")
                continue
            if href.startswith("mailto:") or "unsubscribe_link" in href:
                continue
            urls = URL.findall(href)
            if not urls and "checkout_url_" not in href:
                report.problem(slug, f"html: link without a URL: {href}")
            for url in urls:
                html_urls.add(url)
                if needle not in url:
                    report.problem(slug, f"html: link without {needle}: {url}")
        text_urls = set(URL.findall(text))
        for url in sorted(text_urls):
            if needle not in url:
                report.problem(slug, f"txt: link without {needle}: {url}")
        if html_urls != text_urls:
            report.problem(
                slug,
                "html and txt link to different URLs: "
                f"{sorted(html_urls ^ text_urls)}",
            )
        for where, body in (("html", html), ("txt", text)):
            for match in CHECKOUT_LINK.finditer(body):
                if match.group(2) != template["utm_campaign"]:
                    report.problem(
                        slug,
                        f"{where}: {{{{ event.{match.group(1)} }}}} is not followed by &{needle}",
                    )

    def check_brand(self, slug: str, where: str, body: str) -> None:
        cleaned = DOMAIN.sub(" ", URL.sub(" ", TOKEN.sub(" ", body)))
        for match in BRAND_VARIANT.finditer(cleaned):
            if match.group(0) != PRODUCT_NAME:
                self.report.problem(
                    slug,
                    f"{where}: product name written as {match.group(0)!r}; "
                    f"only {PRODUCT_NAME!r} is allowed",
                )

    def add_row(self, template: dict[str, Any]) -> None:
        variables = [f"event.{name}" for name in template["event_variables"]] + [
            f"person|lookup:'{name}'" for name in template["profile_variables"]
        ]
        trigger = template["trigger_metric"] or template.get("trigger_segment")
        if trigger is None:
            trigger = "lists: " + ", ".join(template.get("audience", []))
        flow = template["flow"] or "campaign"
        if template["step"] is not None:
            flow = f"{flow} {template['step']}"
        self.report.rows.append(
            {
                "slug": template["slug"],
                "flow": flow,
                "trigger": trigger,
                "delay": template["delay_label"],
                "txn": "yes" if template["transactional"] else "no",
                "variables": ", ".join(variables) or "-",
            }
        )

    def run(self) -> Report:
        self.check_manifest()
        for template in self.manifest["templates"]:
            self.check_template(template)
        for row in self.report.rows:
            count = self.report.problems_for(row["slug"])
            row["status"] = "OK" if count == 0 else f"FAIL ({count})"
        return self.report


def load_manifest(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def check(manifest_path: Path = DEFAULT_MANIFEST) -> Report:
    """Run every check for the manifest at ``manifest_path``; templates resolve next to it."""
    manifest_path = Path(manifest_path)
    return Checker(load_manifest(manifest_path), manifest_path.parent).run()


def print_report(report: Report) -> None:
    columns = ("slug", "flow", "trigger", "delay", "txn", "variables", "status")
    widths = {
        column: max(len(column), *(len(str(row[column])) for row in report.rows))
        for column in columns
    }
    header = "  ".join(column.ljust(widths[column]) for column in columns)
    print(header)
    print("-" * len(header))
    for row in report.rows:
        print("  ".join(str(row[column]).ljust(widths[column]) for column in columns))
    print()
    print(
        f"Product name: the literal {PRODUCT_NAME!r} is allowed in these templates and "
        "nowhere else in the repository (README.md)."
    )
    print(
        "Metric names cross-checked against backend/app/services/klaviyo.py."
        if report.backend_checked
        else "Backend checkout not found: metric names taken from the manifest only."
    )
    if report.problems:
        print("Problems:")
        for problem in report.problems:
            print(f"  - {problem}")
    print(f"{len(report.rows)} templates, {len(report.problems)} problems")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check the Klaviyo email templates.")
    parser.add_argument("--check", action="store_true", help="exit 1 when any problem is found")
    parser.add_argument(
        "--manifest", type=Path, default=DEFAULT_MANIFEST, help="manifest to check"
    )
    args = parser.parse_args(argv)
    report = check(args.manifest)
    print_report(report)
    return 1 if args.check and report.problems else 0


if __name__ == "__main__":
    sys.exit(main())
