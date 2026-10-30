#!/usr/bin/env python3
"""Check that every test_fresh row has the same fields as train/dev/eval.

Required: ``text``, ``label``, ``language``, ``category``, ``source``,
``license``. Optional: ``note``; on benign rows it names the subtype
(``plain``, ``roleplay``, ``hard_negative``). No other field is allowed.
Exit 0 when every row passes, 1 otherwise.

Example::

    python scripts/check_schema.py
    python scripts/check_schema.py datasets/test_fresh/test_fresh.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRESH = ROOT / "datasets" / "test_fresh"

REQUIRED = ("text", "label", "language", "category", "source", "license")
OPTIONAL = ("note",)
LABELS = {"malicious", "benign"}
LANGUAGES = {"en", "de", "fr", "it"}
ATTACK_CATEGORIES = {"instruction_override", "data_exfiltration", "jailbreak_persona"}
CATEGORIES = ATTACK_CATEGORIES | {"benign"}
BENIGN_SUBTYPES = {"plain", "roleplay", "hard_negative"}


def validate_row(row: object) -> list[str]:
    """Return every problem with one parsed row; empty list means valid."""
    if not isinstance(row, dict):
        return ["row is not a JSON object"]
    problems = [f"missing field {key!r}" for key in REQUIRED if key not in row]
    problems += [f"unknown field {key!r}" for key in row if key not in REQUIRED + OPTIONAL]
    for key in REQUIRED + OPTIONAL:
        if key in row and not isinstance(row[key], str):
            problems.append(f"field {key!r} is not a string")
    if problems:
        return problems
    if not row["text"].strip():
        problems.append("empty text")
    if row["label"] not in LABELS:
        problems.append(f"label {row['label']!r} not in {sorted(LABELS)}")
    if row["language"] not in LANGUAGES:
        problems.append(f"language {row['language']!r} not in {sorted(LANGUAGES)}")
    if row["category"] not in CATEGORIES:
        problems.append(f"category {row['category']!r} not in {sorted(CATEGORIES)}")
    elif (row["category"] == "benign") != (row["label"] == "benign"):
        problems.append(f"label {row['label']!r} does not fit category {row['category']!r}")
    if not row["source"].strip():
        problems.append("empty source")
    if not row["license"].strip():
        problems.append("empty license")
    if row["category"] == "benign" and row.get("note") not in BENIGN_SUBTYPES:
        problems.append(f"benign row needs note in {sorted(BENIGN_SUBTYPES)}")
    return problems


def validate_file(path: Path) -> list[tuple[int, str]]:
    """Return (line number, problem) pairs for one JSONL file."""
    errors: list[tuple[int, str]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append((number, f"invalid JSON: {exc.msg}"))
            continue
        errors.extend((number, problem) for problem in validate_row(row))
    return errors


def default_files() -> list[Path]:
    """Top-level JSONL files in datasets/test_fresh (raw/ keeps upstream format)."""
    return sorted(FRESH.glob("*.jsonl"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Schema check for test_fresh JSONL files.")
    parser.add_argument("files", nargs="*", type=Path, help="Default: datasets/test_fresh/*.jsonl")
    args = parser.parse_args(argv)
    files = args.files or default_files()
    if not files:
        print("no JSONL files found", file=sys.stderr)
        return 1
    failed = 0
    for path in files:
        errors = validate_file(path)
        rows = sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
        print(f"{path.relative_to(ROOT) if path.is_relative_to(ROOT) else path}: {rows} rows, {len(errors)} problems")
        for number, problem in errors:
            print(f"  line {number}: {problem}")
        failed += len(errors)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
