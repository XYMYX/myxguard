"""Load phrase rules from ``data/patterns/*.json`` and run them.

Contributors add a language by dropping a new JSON file in that folder.
See CONTRIBUTING.md. The loader checks that every rule matches its own
``example`` and does not match its ``benign_example``, so a broken regex
fails as soon as the rules are read.

Some English, German, and French expressions are adapted from prompt-guard
(MIT, Seojoon Kim) and from Vigil's YARA rules (Apache-2.0, Adam M. Swanda).
The JSON ``_meta`` block and THIRD_PARTY_NOTICES.md record what changed.
Italian, Swiss German, and the tighter false-positive guards are original.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Optional, Sequence

from myxguard.models import SEVERITIES, Finding, make_finding

# User-facing language codes. "multi" is the always-on pack (common.json).
KNOWN_LANGUAGES = ("en", "de", "fr", "it", "gsw")

# Phrase categories a JSON file is allowed to use. Structural detectors
# (Unicode, HTML) use their own categories in Python.
PATTERN_CATEGORIES = {
    "instruction_override",
    "role_impersonation",
    "data_exfiltration",
    "tool_abuse",
    "jailbreak_persona",
    "delimiter_injection",
}

_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "patterns"
_MAX_MATCHES_PER_RULE = 8
_UNBOUNDED_DOT = re.compile(r"(?<!\\)\.(?:\*|\+)")


@dataclass(frozen=True)
class Rule:
    """One compiled regular expression from a language pack."""

    rule_id: str
    language: str
    category: str
    severity: str
    explanation: str
    regex: re.Pattern[str]


def expand_languages(languages: Sequence[str]) -> tuple[str, ...]:
    """Normalize codes. German also loads Swiss German (``gsw``)."""
    ordered: list[str] = []
    for language in languages:
        if not isinstance(language, str):
            raise TypeError("languages must be a list of language codes, not a nested value.")
        code = language.strip().lower()
        if not code:
            continue
        extras = ("de", "gsw") if code == "de" else (code,)
        for extra in extras:
            if extra not in ordered:
                ordered.append(extra)
    return tuple(ordered)


def get_rules(languages: Optional[Sequence[str]] = None) -> tuple[Rule, ...]:
    """Return the compiled rules for ``languages`` (``None`` means all)."""
    if languages is None:
        return _load_cached(None)
    if isinstance(languages, str):
        raise TypeError(
            "languages must be a list of codes, for example ['en', 'de'], not a string."
        )
    return _load_cached(expand_languages(languages))


def scan_patterns(text: str, languages: Optional[Sequence[str]] = None) -> list[Finding]:
    """Find phrase rules in ``text``. Offsets refer to ``text`` as given."""
    findings: list[Finding] = []
    for rule in get_rules(languages):
        matches = 0
        for match in rule.regex.finditer(text):
            matches += 1
            if matches > _MAX_MATCHES_PER_RULE:
                break
            if match.end() <= match.start():
                continue
            findings.append(
                make_finding(
                    text,
                    match.start(),
                    match.end(),
                    rule_id=rule.rule_id,
                    category=rule.category,
                    severity=rule.severity,
                    explanation=rule.explanation,
                    language=rule.language,
                )
            )
    return findings


@lru_cache(maxsize=16)
def _load_cached(key: Optional[tuple[str, ...]]) -> tuple[Rule, ...]:
    packs = _read_packs()
    if key is not None:
        unknown = [code for code in key if code not in KNOWN_LANGUAGES]
        if unknown:
            known = ", ".join(KNOWN_LANGUAGES)
            raise ValueError(
                f"Unknown language code(s): {', '.join(unknown)}. Known codes: {known}."
            )
        selected = set(key)
    else:
        selected = set(KNOWN_LANGUAGES)

    rules: list[Rule] = []
    seen_ids: set[str] = set()
    for language, items in packs:
        if language != "multi" and language not in selected:
            continue
        for item in items:
            rule = _compile_item(language, item, seen_ids)
            rules.append(rule)
    return tuple(rules)


def _read_packs() -> tuple[tuple[str, list[dict]], ...]:
    if not _DATA_DIR.is_dir():
        raise FileNotFoundError(f"Pattern directory is missing: {_DATA_DIR}")
    packs = []
    for path in sorted(_DATA_DIR.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path.name} is not valid JSON: {exc}") from exc
        meta = data.get("_meta")
        if not isinstance(meta, dict) or "language" not in meta:
            raise ValueError(f"{path.name} needs a _meta.language field.")
        patterns = data.get("patterns")
        if not isinstance(patterns, list):
            raise ValueError(f"{path.name} needs a patterns list.")
        packs.append((str(meta["language"]), patterns))
    return tuple(packs)


def _compile_item(language: str, item: dict, seen_ids: set[str]) -> Rule:
    rule_id = str(item.get("id", ""))
    if not rule_id:
        raise ValueError(f"A {language} pattern is missing id.")
    if rule_id in seen_ids:
        raise ValueError(f"Duplicate pattern id {rule_id}.")
    seen_ids.add(rule_id)

    category = str(item.get("category", ""))
    if category not in PATTERN_CATEGORIES:
        allowed = ", ".join(sorted(PATTERN_CATEGORIES))
        raise ValueError(f"{rule_id} has unknown category {category!r}. Use one of: {allowed}.")

    severity = str(item.get("severity", ""))
    if severity not in SEVERITIES:
        raise ValueError(f"{rule_id} has unknown severity {severity!r}.")

    explanation = str(item.get("explanation", "")).strip()
    example = item.get("example")
    if not explanation or not isinstance(example, str) or not example:
        raise ValueError(f"{rule_id} needs an explanation and an example.")

    raw_regex = str(item.get("regex", ""))
    if _UNBOUNDED_DOT.search(raw_regex):
        raise ValueError(
            f"{rule_id} uses an unbounded '.' repeat. "
            "Use a bounded one such as '.{0,40}' so a long input cannot hang the scanner."
        )
    try:
        compiled = re.compile(raw_regex)
    except re.error as exc:
        raise ValueError(f"{rule_id} has an invalid regex: {exc}") from exc

    if compiled.search(example) is None:
        raise ValueError(f"{rule_id} does not match its example: {example!r}")
    benign = item.get("benign_example")
    if isinstance(benign, str) and benign and compiled.search(benign):
        raise ValueError(f"{rule_id} also matches its benign_example: {benign!r}")

    return Rule(
        rule_id=rule_id,
        language=language,
        category=category,
        severity=severity,
        explanation=explanation,
        regex=compiled,
    )
