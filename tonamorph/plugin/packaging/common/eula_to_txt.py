#!/usr/bin/env python3
"""Render legal/eula.md to the plain text the installers embed.

Standard library only, so it runs on every CI runner as-is:

    eula_to_txt.py INPUT.md OUTPUT.txt [--missing-ok] [--unresolved-ok | --keep-unresolved]
                   [--placeholder-title T]

Also used for THIRD_PARTY_LICENSES.md (same placeholder set and comment syntax).

Conversion: HTML comments are removed, headings become upper-case lines, list items become
"- item", tables become tab-separated rows, inline emphasis/code/links are flattened.
Every [[PLACEHOLDER]] token is substituted from the environment variable of the same name
(PRODUCT_NAME, COMPANY_LEGAL_NAME, ...); a token that is still present afterwards is an
error, because an installer must never ship a licence with blanks in it. --unresolved-ok
replaces the whole document with a placeholder text instead (dry-run installers);
--keep-unresolved converts the document and leaves the unresolved [[TOKENS]] in place
(the plugin's About screen, which is built on machines without the company variables).

Exit codes: 0 converted (or a placeholder was written under --missing-ok/--unresolved-ok),
2 unresolved placeholders, 3 input file missing, 1 usage.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Mapping, Sequence

PLACEHOLDER_NAMES: tuple[str, ...] = (
    "PRODUCT_NAME",
    "COMPANY_LEGAL_NAME",
    "COMPANY_ADDRESS",
    "COMPANY_REG_ID",
    "WEBSITE_URL",
    "SUPPORT_EMAIL",
    "PRIVACY_EMAIL",
    "LEGAL_EMAIL",
    "MERCHANT_OF_RECORD",
    "EFFECTIVE_DATE",
    "EFFECTIVE_YEAR",
)

_PLACEHOLDER_RE = re.compile(r"\[\[([A-Z][A-Z0-9_]*)\]\]")
_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
_LIST_RE = re.compile(r"^(\s*)(?:[-*+]|\d+[.)])\s+(.*)$")
_TABLE_SEPARATOR_RE = re.compile(r"^\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?$")
_RULE_RE = re.compile(r"^\s*([-*_])(\s*\1){2,}\s*$")
_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
_AUTOLINK_RE = re.compile(r"<(https?://[^>]+|[^\s>]+@[^\s>]+)>")
_STRONG_RE = re.compile(r"(\*\*|__)(.+?)\1")
_EMPHASIS_RE = re.compile(r"(?<![\w*])(\*|_)(?!\s)(.+?)(?<!\s)\1(?![\w*])")
_CODE_RE = re.compile(r"`([^`]*)`")
_TAG_RE = re.compile(r"</?(br|b|i|em|strong|u|p|sup|sub)\s*/?>", re.IGNORECASE)


class UnresolvedPlaceholderError(ValueError):
    """Raised when a [[TOKEN]] has no value."""

    def __init__(self, names: Sequence[str]) -> None:
        self.names = tuple(sorted(set(names)))
        super().__init__("unresolved placeholders: " + ", ".join(self.names))


def substitute_placeholders(text: str, values: Mapping[str, str], keep_unresolved: bool = False) -> str:
    """Replace every [[TOKEN]] that has a value. A token without one raises, or is left
    verbatim when ``keep_unresolved`` is set."""
    missing: list[str] = []

    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        value = values.get(name, "")
        if not value.strip():
            missing.append(name)
            return match.group(0)
        return value

    result = _PLACEHOLDER_RE.sub(replace, text)
    if missing and not keep_unresolved:
        raise UnresolvedPlaceholderError(missing)
    return result


def _inline(text: str) -> str:
    text = _CODE_RE.sub(r"\1", text)
    text = _LINK_RE.sub(r"\1 (\2)", text)
    text = _AUTOLINK_RE.sub(r"\1", text)
    text = _STRONG_RE.sub(r"\2", text)
    text = _EMPHASIS_RE.sub(r"\2", text)
    text = _TAG_RE.sub("", text)
    text = text.replace("\\*", "*").replace("\\_", "_").replace("\\#", "#")
    return text.rstrip()


def _table_row(line: str) -> str:
    cells = line.strip().strip("|").split("|")
    return "\t".join(_inline(cell.strip()) for cell in cells)


def markdown_to_text(markdown: str) -> str:
    """Flatten Markdown to plain text. Placeholders are left alone here."""
    markdown = _COMMENT_RE.sub("", markdown)
    out: list[str] = []
    in_fence = False
    for raw in markdown.splitlines():
        line = raw.rstrip()
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            out.append(line)
            continue
        if not line.strip():
            out.append("")
            continue
        if _RULE_RE.match(line):
            out.append("")
            continue
        heading = _HEADING_RE.match(line)
        if heading:
            out.extend(["", _inline(heading.group(2)).upper(), ""])
            continue
        if line.lstrip().startswith("|"):
            if _TABLE_SEPARATOR_RE.match(line.strip()):
                continue
            out.append(_table_row(line))
            continue
        item = _LIST_RE.match(line)
        if item:
            out.append(f"{item.group(1)}- {_inline(item.group(2))}")
            continue
        if line.lstrip().startswith(">"):
            line = line.lstrip()[1:].lstrip()
        out.append(_inline(line))

    text = "\n".join(out)
    text = re.sub(r"\n{3,}", "\n\n", text).strip("\n")
    return text + "\n"


def convert(markdown: str, values: Mapping[str, str], keep_unresolved: bool = False) -> str:
    """Substitute placeholders, then flatten. Raises UnresolvedPlaceholderError unless
    ``keep_unresolved`` leaves the tokens in the text."""
    return markdown_to_text(substitute_placeholders(markdown, values, keep_unresolved))


def unresolved_placeholders(text: str) -> tuple[str, ...]:
    """The [[TOKEN]] names still present in a converted text (for --keep-unresolved warnings)."""
    return tuple(sorted(set(_PLACEHOLDER_RE.findall(text))))


def placeholder_text(product_name: str, reason: str, title: str, source: str) -> str:
    name = product_name or "this product"
    return (
        f"{title.upper()} - PLACEHOLDER\n"
        "\n"
        f"The {title.lower()} text for {name} was not available when this installer was built\n"
        f"({reason}).\n"
        "\n"
        "THIS BUILD IS FOR INTERNAL TESTING ONLY AND MUST NOT BE DISTRIBUTED.\n"
        f"Add {source} (and the COMPANY_* / *_EMAIL / EFFECTIVE_* repository variables)\n"
        "and rebuild the release before publishing it.\n"
    )


def values_from_environment(environ: Mapping[str, str] = os.environ) -> dict[str, str]:
    return {name: environ.get(name, "") for name in PLACEHOLDER_NAMES}


def _warn(message: str) -> None:
    print(f"eula_to_txt: WARNING: {message}", file=sys.stderr)
    if os.environ.get("GITHUB_ACTIONS"):
        print(f"::warning::{message}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("input", type=Path, help="Markdown EULA, normally legal/eula.md")
    parser.add_argument("output", type=Path, help="plain-text file to write")
    parser.add_argument(
        "--missing-ok",
        action="store_true",
        help="write a placeholder licence and warn when INPUT does not exist",
    )
    parser.add_argument(
        "--placeholder-title",
        default="End User Licence Agreement",
        help="heading of the placeholder text (e.g. 'Third-Party Notices')",
    )
    unresolved = parser.add_mutually_exclusive_group()
    unresolved.add_argument(
        "--unresolved-ok",
        action="store_true",
        help="write a placeholder licence and warn when [[TOKENS]] have no value (dry runs only)",
    )
    unresolved.add_argument(
        "--keep-unresolved",
        action="store_true",
        help="convert the document and leave [[TOKENS]] without a value in the text, with a warning",
    )
    args = parser.parse_args(argv)
    values = values_from_environment()
    product_name = values["PRODUCT_NAME"]

    if not args.input.is_file():
        if not args.missing_ok:
            print(f"eula_to_txt: ERROR: {args.input} does not exist", file=sys.stderr)
            return 3
        _warn(
            f"{args.input} does not exist; the installer licence is a PLACEHOLDER."
            " Do not publish this release."
        )
        text = placeholder_text(product_name, f"{args.input.name} is missing", args.placeholder_title, args.input.name)
    elif args.keep_unresolved:
        text = convert(args.input.read_text(encoding="utf-8"), values, keep_unresolved=True)
        if names := unresolved_placeholders(text):
            _warn(f"unresolved placeholders left in the text: {', '.join(names)}")
    else:
        try:
            text = convert(args.input.read_text(encoding="utf-8"), values)
        except UnresolvedPlaceholderError as error:
            if not args.unresolved_ok:
                print(
                    f"eula_to_txt: ERROR: {error}; set the repository variables of the same"
                    " names before building a release",
                    file=sys.stderr,
                )
                return 2
            _warn(f"{error}; the installer licence is a PLACEHOLDER. Do not publish this release.")
            text = placeholder_text(product_name, str(error), args.placeholder_title, args.input.name)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text, encoding="utf-8", newline="\n")
    print(f"eula_to_txt: wrote {args.output} ({len(text.splitlines())} lines)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
