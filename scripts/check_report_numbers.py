#!/usr/bin/env python3
"""Check that every number in the report's tables comes from the raw eval JSON.

Allowed in a table cell: integers found in the raw files, and every float
from them written as ``0.947`` (three decimals) or as a percentage ``12.5``
(one decimal). Header rows (the line above ``|---|``) are skipped. Prose
outside tables is not checked. The report must also name the ``data_sha256``
of each raw file. Exit 0 when nothing is out of place, 1 otherwise.

Example::

    python scripts/check_report_numbers.py reports/eval_2026-11-05.md
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NUMBER = re.compile(r"(?<![\w.])\d+(?:\.\d+)?(?![\w.])")
SEPARATOR = re.compile(r"^\|\s*:?-{3,}")


def _walk(value, ints: set[str], floats: list[float]) -> None:
    if isinstance(value, bool):
        return
    if isinstance(value, int):
        ints.add(str(value))
    elif isinstance(value, float):
        floats.append(value)
    elif isinstance(value, dict):
        for item in value.values():
            _walk(item, ints, floats)
    elif isinstance(value, list):
        for item in value:
            _walk(item, ints, floats)


def allowed_numbers(raw_files: list[Path]) -> tuple[set[str], set[str]]:
    """Allowed number strings, and the data hashes the report must mention."""
    ints: set[str] = set()
    floats: list[float] = []
    hashes: set[str] = set()
    for path in raw_files:
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("data_sha256"):
            hashes.add(data["data_sha256"])
        data = {key: value for key, value in data.items() if key not in {"scores", "errors"}}
        _walk(data, ints, floats)
    allowed = set(ints)
    for value in floats:
        allowed.add(f"{value:.3f}")
        allowed.add(f"{value * 100:.1f}")
    return allowed, hashes


def check_report(report: Path, raw_files: list[Path]) -> list[str]:
    allowed, hashes = allowed_numbers(raw_files)
    text = report.read_text(encoding="utf-8")
    problems = [f"report does not name data sha256 {digest[:12]}" for digest in sorted(hashes)
                if digest not in text and digest[:12] not in text]
    lines = text.splitlines()
    for number, line in enumerate(lines, 1):
        if not line.lstrip().startswith("|") or SEPARATOR.match(line.strip()):
            continue
        following = lines[number] if number < len(lines) else ""
        if SEPARATOR.match(following.strip()):
            continue  # header row
        for token in NUMBER.findall(line):
            if token not in allowed:
                problems.append(f"line {number}: {token} not in raw eval files")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check report numbers against raw eval JSON.")
    parser.add_argument("report", type=Path)
    parser.add_argument("raw", nargs="*", type=Path, help="Default: reports/raw/eval_*_<date of report>.json")
    args = parser.parse_args(argv)
    raw = args.raw
    if not raw:
        date = re.search(r"\d{4}-\d{2}-\d{2}", args.report.name)
        raw = sorted((ROOT / "reports" / "raw").glob(f"eval_*_{date.group(0) if date else '*'}.json"))
    if not raw:
        print("no raw eval files found", file=sys.stderr)
        return 1
    problems = check_report(args.report, raw)
    for problem in problems:
        print(problem)
    print(f"{len(problems)} problems in {args.report.name} against {len(raw)} raw files")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
