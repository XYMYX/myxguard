#!/usr/bin/env python3
"""Convert hand-written lines ``sprache|label|kategorie|text`` to handwritten_<lang>.jsonl.

Format as in training/experiments/make_fresh.py. Attack categories stay as
they are. Benign categories become ``category: benign`` with the subtype in
``note``: ``normal``/``plain`` -> ``plain``, ``hard_negative``, ``roleplay``.
Several source files are read in order and written together.
Lines starting with ``#`` and empty lines are skipped. Any other malformed
line stops the run, so nothing is dropped silently. ``--dry-run`` prints the
counts without writing.

Example::

    python scripts/convert_fresh_raw.py datasets/test_fresh/raw/fresh_raw1.txt datasets/test_fresh/raw/fresh_raw2.txt
"""

from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.check_schema import ATTACK_CATEGORIES, LANGUAGES, validate_row  # noqa: E402

FRESH = ROOT / "datasets" / "test_fresh"
BENIGN_NOTE = {"normal": "plain", "plain": "plain", "hard_negative": "hard_negative", "roleplay": "roleplay"}
SOURCE = "myxguard-fresh-handwritten"


def parse_line(line: str) -> dict:
    parts = line.split("|", 3)
    if len(parts) != 4:
        raise ValueError("expected sprache|label|kategorie|text")
    language, label, category, text = (part.strip() for part in parts)
    row = {"text": text, "label": label, "language": language, "category": category,
           "source": SOURCE, "license": "MIT"}
    if label == "benign":
        if category not in BENIGN_NOTE:
            raise ValueError(f"unknown benign category {category!r}")
        row["category"] = "benign"
        row["note"] = BENIGN_NOTE[category]
    elif category not in ATTACK_CATEGORIES:
        raise ValueError(f"unknown attack category {category!r}")
    problems = validate_row(row)
    if problems:
        raise ValueError("; ".join(problems))
    return row


def main(argv: list[str] | None = None) -> int:
    sys.stdout.reconfigure(errors="replace")
    parser = argparse.ArgumentParser(description="Convert hand-written fresh lines to JSONL.")
    parser.add_argument("sources", nargs="+", type=Path, help="One or more files, e.g. raw/fresh_raw1.txt raw/fresh_raw2.txt")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    rows, errors = [], []
    for source in args.sources:
        for number, line in enumerate(source.read_text(encoding="utf-8-sig").splitlines(), 1):
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            try:
                rows.append(parse_line(line))
            except ValueError as exc:
                errors.append(f"{source.name} line {number}: {exc}")
    for error in errors:
        print(error)
    if errors:
        print(f"{len(errors)} malformed lines, nothing written", file=sys.stderr)
        return 1

    counts = collections.Counter(
        f"{row['language']}/{row['category']}" + (f"/{row['note']}" if "note" in row else "") for row in rows
    )
    for key, value in sorted(counts.items()):
        print(f"  {key}: {value}")
    print(f"{len(rows)} rows")
    if args.dry_run:
        return 0
    for language in sorted(LANGUAGES):
        out = FRESH / f"handwritten_{language}.jsonl"
        lines = [json.dumps(row, ensure_ascii=False) + "\n" for row in rows if row["language"] == language]
        out.write_text("".join(lines), encoding="utf-8")
        print(f"{len(lines)} rows -> {out.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
