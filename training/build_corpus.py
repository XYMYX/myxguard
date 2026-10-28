#!/usr/bin/env python3
"""Build datasets/train/train.jsonl from licensed sources and original text.

The held-out eval file and the dev set are block lists. A row is dropped when
its normalized text matches or sits close to either file. Dev stays the
validation split. Re-running this script needs network access for Tatoeba and,
on a cold cache, for the Hugging Face parquet files.

    python training/build_corpus.py
"""

from __future__ import annotations

import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

import duckdb

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from training.dedupe import NearDupIndex, normalize
from training.original_rows import generate
from training.public_rows import ensure_parquet, load_public

_TARGETS = {
    "en": {"benign": 260, "malicious": 260},
    "de": {"benign": 260, "malicious": 260},
    "fr": {"benign": 260, "malicious": 260},
    "it": {"benign": 260, "malicious": 260},
    "gsw": {"benign": 260, "malicious": 260},
}
_ALLOWED = {"MIT", "Apache-2.0", "CC-BY-4.0", "CC-BY-2.0-FR", "CC0-1.0"}
_FIELDS = ("text", "label", "language", "category", "source", "license")


def main() -> int:
    rng = random.Random(20261026)
    heldout = _ROOT / "datasets" / "eval" / "heldout.jsonl"
    dev = _ROOT / "datasets" / "dev" / "dev.jsonl"
    samples = _ROOT / "datasets" / "samples.jsonl"
    blocked = NearDupIndex(_texts(heldout) + _texts(dev))
    sample_exact = {normalize(text) for text in _texts(samples)}

    tables = {
        key: _read_parquet(ensure_parquet(_ROOT, key))
        for key in ("deepset", "deepset_test", "neuralchemy", "enes", "shomi")
    }
    public, skipped = load_public(tables, rng)
    original = generate(rng)
    incoming = public + original

    report = {
        "public_loaded": len(public),
        "original_loaded": len(original),
        "skipped_upstream": skipped,
        "dropped": Counter(),
    }
    kept: list[dict[str, str]] = []
    seen: set[str] = set()
    for row in incoming:
        folded = normalize(row["text"])
        if not folded:
            report["dropped"]["empty"] += 1
            continue
        if folded in sample_exact:
            report["dropped"]["samples_exact"] += 1
            continue
        reason = blocked.reason(row["text"])
        if reason is not None:
            report["dropped"][f"blocked_{reason}"] += 1
            continue
        if folded in seen:
            report["dropped"]["internal_exact"] += 1
            continue
        if row["license"] not in _ALLOWED:
            report["dropped"]["license"] += 1
            continue
        seen.add(folded)
        kept.append(row)

    selected = _select(kept, rng)
    selected.sort(key=lambda row: (row["language"], row["label"], row["category"], row["source"], row["text"]))
    out_dir = _ROOT / "datasets" / "train"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "train.jsonl"
    with out_path.open("w", encoding="utf-8") as handle:
        for row in selected:
            handle.write(json.dumps({key: row[key] for key in _FIELDS}, ensure_ascii=False) + "\n")

    summary = _summary(selected)
    summary["dropped"] = dict(report["dropped"])
    summary["skipped_upstream"] = skipped
    summary["public_loaded"] = report["public_loaded"]
    summary["original_loaded"] = report["original_loaded"]
    summary["kept_before_cap"] = len(kept)
    (out_dir / "build_report.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (out_dir / "README.md").write_text(_readme(summary), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


def _select(rows: list[dict[str, str]], rng: random.Random) -> list[dict[str, str]]:
    pools: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        pools[(row["language"], row["label"])].append(row)
    chosen: list[dict[str, str]] = []
    for language, labels in _TARGETS.items():
        for label, cap in labels.items():
            chosen.extend(_round_robin(pools[(language, label)], cap, rng))
    return chosen


def _round_robin(rows: list[dict[str, str]], cap: int, rng: random.Random) -> list[dict[str, str]]:
    by_category: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_category[row["category"]].append(row)
    for bucket in by_category.values():
        rng.shuffle(bucket)
    names = sorted(by_category)
    picked: list[dict[str, str]] = []
    while len(picked) < cap and any(by_category.values()):
        for name in names:
            bucket = by_category[name]
            if not bucket:
                continue
            picked.append(bucket.pop())
            if len(picked) >= cap:
                break
    return picked


def _read_parquet(path: Path) -> list[dict]:
    connection = duckdb.connect()
    connection.execute(f"SELECT * FROM read_parquet('{path.as_posix()}')")
    columns = [item[0] for item in connection.description]
    return [dict(zip(columns, row)) for row in connection.fetchall()]


def _texts(path: Path) -> list[str]:
    texts = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            texts.append(json.loads(line)["text"])
    return texts


def _summary(rows: list[dict[str, str]]) -> dict:
    return {
        "rows": len(rows),
        "label": dict(Counter(row["label"] for row in rows)),
        "language": dict(Counter(row["language"] for row in rows)),
        "category": dict(Counter(row["category"] for row in rows)),
        "source": dict(Counter(_source_family(row["source"]) for row in rows)),
        "license": dict(Counter(row["license"] for row in rows)),
        "language_label": {
            f"{language}:{label}": count
            for (language, label), count in Counter(
                (row["language"], row["label"]) for row in rows
            ).items()
        },
        "language_category": {
            f"{language}:{category}": count
            for (language, category), count in Counter(
                (row["language"], row["category"]) for row in rows
            ).items()
        },
    }


def _source_family(source: str) -> str:
    if source.startswith("tatoeba.org:"):
        return "tatoeba.org"
    return source


def _readme(summary: dict) -> str:
    def table(title: str, mapping: dict) -> str:
        lines = [f"## {title}", "", "| key | rows |", "| --- | ---: |"]
        for key in sorted(mapping):
            lines.append(f"| {key} | {mapping[key]} |")
        lines.append("")
        return "\n".join(lines)

    return "\n".join(
        [
            "# Training corpus",
            "",
            "`train.jsonl` is the default input of `training/finetune.py`.",
            "Each row has `text`, `label` (`malicious` or `benign`), `language`, `category`, `source`, and `license`.",
            "",
            "Nothing in this file is copied from `datasets/eval/heldout.jsonl`.",
            "The build also drops near-duplicates of that file and of `datasets/dev/dev.jsonl`.",
            "Dev stays the validation split and is not mixed into these rows.",
            "",
            "Rebuild (needs network for Tatoeba, and for Hugging Face if the cache is empty):",
            "",
            "```bash",
            "python training/build_corpus.py",
            "python scripts/dataset_stats.py datasets/train/train.jsonl",
            "```",
            "",
            f"Rows in this build: {summary['rows']}.",
            "",
            "The builder drops exact and near-duplicate rows from the held-out file and the dev set before the cap.",
            "Counts for the last run are in `build_report.json` under `dropped` and `skipped_upstream`.",
            "",
            table("Label", summary["label"]),
            table("Language", summary["language"]),
            table("Category", summary["category"]),
            table("Source", summary["source"]),
            table("License", summary["license"]),
            "Sources and the license check are recorded in `THIRD_PARTY_NOTICES.md`.",
            "Original rows use source `myxguard-train-original` and the MIT license of this package.",
            "",
        ]
    )


if __name__ == "__main__":
    raise SystemExit(main())
