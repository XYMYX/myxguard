#!/usr/bin/env python3
"""Build datasets/test_fresh/test_fresh.jsonl from Gandalf and hand-written rows.

Gandalf: drop rows that the leakage check would flag (blocked files, near-
duplicates inside the pool, text that normalizes to nothing), then draw a
fixed sample with ``random.Random(20261030)``. Every row becomes
``instruction_override`` in English. The detector is never run here.
Hand-written rows from ``handwritten_<lang>.jsonl`` are copied as they are.
Writes ``test_fresh.jsonl`` and ``build_report.json`` (counts per language,
category, benign subtype and source, plus cells below the plan targets).
Exit 0 when the file was written and every row passes the schema check.

Example::

    python scripts/build_test_fresh.py
"""

from __future__ import annotations

import collections
import hashlib
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.check_leakage import BLOCK_FILES, find_leaks, read_texts  # noqa: E402
from scripts.check_schema import ATTACK_CATEGORIES, LANGUAGES, validate_row  # noqa: E402

FRESH = ROOT / "datasets" / "test_fresh"
RAW = FRESH / "raw" / "gandalf_ignore_instructions.jsonl"
META = FRESH / "raw" / "gandalf_ignore_instructions.meta.json"
OUT = FRESH / "test_fresh.jsonl"
REPORT = FRESH / "build_report.json"
SEED = 20261030
GANDALF_SAMPLE = 50
# Plan A3: per language, at least this many rows per cell.
TARGET_ATTACK = 15
TARGET_BENIGN = 45
TARGET_BENIGN_SUBTYPE = {"roleplay": 15, "hard_negative": 15}


def gandalf_rows() -> tuple[list[dict], dict]:
    revision = json.loads(META.read_text(encoding="utf-8"))["sha"]
    raw = [json.loads(line) for line in RAW.read_text(encoding="utf-8").splitlines() if line.strip()]
    blocked = {path.name: read_texts(path) for path in BLOCK_FILES}
    hits = find_leaks(raw, blocked)
    dropped = {hit["row"] - 1 for hit in hits}
    pool = [row for index, row in enumerate(raw) if index not in dropped]
    sample = random.Random(SEED).sample(pool, GANDALF_SAMPLE)
    rows = [
        {
            "text": row["text"],
            "label": "malicious",
            "language": "en",
            "category": "instruction_override",
            "source": f"Lakera/gandalf_ignore_instructions@{revision[:8]}:{row['split']}",
            "license": "MIT",
        }
        for row in sample
    ]
    stats = {
        "raw": len(raw),
        "dropped_by_leakage_precheck": dict(collections.Counter(hit["against"] for hit in hits)),
        "pool": len(pool),
        "sampled": len(rows),
        "seed": SEED,
        "revision": revision,
    }
    return rows, stats


def handwritten_rows() -> list[dict]:
    rows = []
    for language in sorted(LANGUAGES):
        path = FRESH / f"handwritten_{language}.jsonl"
        if path.is_file():
            rows += [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return rows


def coverage(rows: list[dict]) -> list[str]:
    """Cells below the plan targets, e.g. 'de/data_exfiltration: 3 < 15'."""
    cells = collections.Counter((row["language"], row["category"]) for row in rows)
    subtypes = collections.Counter((row["language"], row.get("note")) for row in rows if row["category"] == "benign")
    short = []
    for language in sorted(LANGUAGES):
        for category in sorted(ATTACK_CATEGORIES):
            if cells[language, category] < TARGET_ATTACK:
                short.append(f"{language}/{category}: {cells[language, category]} < {TARGET_ATTACK}")
        if cells[language, "benign"] < TARGET_BENIGN:
            short.append(f"{language}/benign: {cells[language, 'benign']} < {TARGET_BENIGN}")
        for subtype, target in TARGET_BENIGN_SUBTYPE.items():
            if subtypes[language, subtype] < target:
                short.append(f"{language}/benign/{subtype}: {subtypes[language, subtype]} < {target}")
    return short


def main() -> int:
    sys.stdout.reconfigure(errors="replace")
    gandalf, gandalf_stats = gandalf_rows()
    rows = gandalf + handwritten_rows()
    problems = [(index, problem) for index, row in enumerate(rows, 1) for problem in validate_row(row)]
    for index, problem in problems:
        print(f"row {index}: {problem}")
    if problems:
        print("schema problems, nothing written", file=sys.stderr)
        return 1

    OUT.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
    counts = collections.Counter(f"{row['language']}/{row['category']}" for row in rows)
    report = {
        "rows": len(rows),
        "sha256": hashlib.sha256(OUT.read_bytes()).hexdigest(),
        "by_language_category": dict(sorted(counts.items())),
        "by_language_benign_subtype": dict(sorted(collections.Counter(
            f"{row['language']}/{row['note']}" for row in rows if row["category"] == "benign"
        ).items())),
        "by_source": dict(sorted(collections.Counter(row["source"].split("@")[0] for row in rows).items())),
        "gandalf": gandalf_stats,
        "below_target": coverage(rows),
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{len(rows)} rows -> {OUT.relative_to(ROOT).as_posix()} (sha256 {report['sha256'][:12]})")
    print(f"below target: {len(report['below_target'])} cells")
    for cell in report["below_target"]:
        print(f"  {cell}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
