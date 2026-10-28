#!/usr/bin/env python3
"""Count rows in a MyxGuard JSONL file.

    python scripts/dataset_stats.py datasets/train/train.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path


def summarize(path: Path) -> dict[str, Counter]:
    labels: Counter = Counter()
    languages: Counter = Counter()
    categories: Counter = Counter()
    sources: Counter = Counter()
    rows = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        rows += 1
        labels[row.get("label", "?")] += 1
        languages[row.get("language", "?")] += 1
        categories[row.get("category", "?")] += 1
        source = str(row.get("source", "?"))
        if source.startswith("tatoeba.org:"):
            source = "tatoeba.org"
        sources[source] += 1
    return {
        "rows": Counter({path.name: rows}),
        "label": labels,
        "language": languages,
        "category": categories,
        "source": sources,
    }


def format_summary(counts: dict[str, Counter]) -> str:
    sections = []
    for name in ("rows", "label", "language", "category", "source"):
        lines = [name]
        for key, value in sorted(counts[name].items()):
            lines.append(f"  {key}: {value}")
        sections.append("\n".join(lines))
    return "\n".join(sections)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Count JSONL rows by language, label, category, and source.")
    parser.add_argument("path", type=Path, nargs="+")
    args = parser.parse_args(argv)
    for path in args.path:
        if not path.is_file():
            print(f"Dataset not found: {path}", file=sys.stderr)
            return 2
        print(format_summary(summarize(path)))
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
