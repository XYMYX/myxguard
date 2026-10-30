#!/usr/bin/env python3
"""Leakage check: test_fresh must not repeat or closely paraphrase known text.

Uses ``training.dedupe.NearDupIndex`` (exact after normalizing, contained,
trigram Jaccard >= 0.80, SequenceMatcher ratio >= 0.86). Blocked: train, dev,
eval, samples, deepset_sample and the used-up fresh set in ../apertus. Rows
inside test_fresh may not duplicate each other either. Must run before every
evaluation. Writes a JSON report with the SHA-256 of each checked file.
Exit 0 on zero hits, 1 on any hit or a missing block file.

Example::

    python scripts/check_leakage.py
    python scripts/check_leakage.py --block ../apertus/dataset.jsonl
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import sys
from pathlib import Path
from typing import Iterable, Mapping, Sequence, Union

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from training.dedupe import NearDupIndex  # noqa: E402

FRESH = ROOT / "datasets" / "test_fresh"
BLOCK_FILES = (
    ROOT / "datasets" / "train" / "train.jsonl",
    ROOT / "datasets" / "dev" / "dev.jsonl",
    ROOT / "datasets" / "eval" / "heldout.jsonl",
    ROOT / "datasets" / "samples.jsonl",
    ROOT / "datasets" / "deepset_sample.jsonl",
    ROOT.parent / "apertus" / "test_fresh.jsonl",
)

Blocked = Union[Mapping[str, Iterable[str]], Iterable[str]]


def find_leaks(rows: Sequence[dict], blocked: Blocked) -> list[dict]:
    """Return one hit per row that matches a blocked text or an earlier row."""
    if not isinstance(blocked, Mapping):
        blocked = {"blocklist": blocked}
    indexes = {name: NearDupIndex(texts) for name, texts in blocked.items()}
    seen = NearDupIndex()
    hits = []
    for number, row in enumerate(rows, 1):
        text = row["text"]
        hit = None
        if seen.reason(text) == "empty":
            # Nothing is left after normalizing (e.g. only non-Latin letters), so
            # near-duplicates cannot be ruled out. Count it as a hit, not as clean.
            hits.append({"row": number, "against": "unchecked", "reason": "empty", "text": text})
            continue
        for name, index in indexes.items():
            reason = index.reason(text)
            if reason is not None:
                hit = (name, reason)
                break
        if hit is None:
            reason = seen.reason(text)
            if reason is not None:
                hit = ("test_fresh", reason)
        if hit is not None:
            hits.append({"row": number, "against": hit[0], "reason": hit[1], "text": text})
        seen.add(text)
    return hits


def read_texts(path: Path) -> list[str]:
    texts = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            texts.append(row["text"] if isinstance(row, dict) else str(row))
    return texts


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _name(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def main(argv: list[str] | None = None) -> int:
    # The Windows console is cp1252; upstream rows carry characters it cannot print.
    sys.stdout.reconfigure(errors="replace")
    parser = argparse.ArgumentParser(description="Leakage check for test_fresh.")
    parser.add_argument("files", nargs="*", type=Path, help="Default: datasets/test_fresh/*.jsonl")
    parser.add_argument("--block", action="append", type=Path, default=[], help="Extra block file (JSONL with text)")
    parser.add_argument("--report", type=Path, help="Default: reports/leakage_<today>.json")
    args = parser.parse_args(argv)

    # Once built, test_fresh.jsonl already holds the hand-written rows; checking
    # both would report every row as a duplicate of itself.
    built = FRESH / "test_fresh.jsonl"
    files = args.files or ([built] if built.is_file() else sorted(FRESH.glob("*.jsonl")))
    block_files = list(BLOCK_FILES) + args.block
    missing = [path for path in block_files if not path.is_file()]
    for path in missing:
        print(f"block file missing: {path}", file=sys.stderr)
    if missing or not files:
        if not files:
            print("no test_fresh files found", file=sys.stderr)
        return 1

    blocked = {_name(path): read_texts(path) for path in block_files}
    rows = []
    origin = []
    for path in files:
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if line.strip():
                rows.append(json.loads(line))
                origin.append((_name(path), number))
    if not rows:
        # An empty set has no leaks to find; that is not a pass.
        print("0 rows in test_fresh: nothing checked", file=sys.stderr)
        return 1
    hits = find_leaks(rows, blocked)
    for hit in hits:
        hit["file"], hit["line"] = origin[hit.pop("row") - 1]

    report = {
        "date": datetime.date.today().isoformat(),
        "checked": {_name(path): sha256(path) for path in files},
        "blocked": {_name(path): {"sha256": sha256(path), "rows": len(blocked[_name(path)])} for path in block_files},
        "rows_checked": len(rows),
        "hits": hits,
    }
    out = args.report or ROOT / "reports" / f"leakage_{report['date']}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"{len(rows)} rows checked against {sum(len(t) for t in blocked.values())} blocked texts: {len(hits)} hits")
    for hit in hits:
        print(f"  {hit['file']}:{hit['line']} [{hit['reason']} vs {hit['against']}] {hit['text'][:100]!r}")
    print(f"report: {_name(out)}")
    return 1 if hits else 0


if __name__ == "__main__":
    raise SystemExit(main())
