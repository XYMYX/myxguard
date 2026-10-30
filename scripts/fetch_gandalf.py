#!/usr/bin/env python3
"""Download Lakera/gandalf_ignore_instructions as JSON rows (no pyarrow needed).

Uses the Hugging Face dataset viewer rows API, 100 rows per request, and
writes the upstream rows unchanged plus their split to
``datasets/test_fresh/raw/gandalf_ignore_instructions.jsonl``. The dataset
revision is read before and after the download; a change aborts the run.
Network access only with the user's approval.

Example::

    python scripts/fetch_gandalf.py
"""

from __future__ import annotations

import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATASET = "Lakera/gandalf_ignore_instructions"
OUT = ROOT / "datasets" / "test_fresh" / "raw" / "gandalf_ignore_instructions.jsonl"
META = OUT.with_suffix(".meta.json")
PAGE = 100


def _get(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=60) as response:
        return json.load(response)


def revision() -> dict:
    info = _get(f"https://huggingface.co/api/datasets/{DATASET}")
    licenses = [tag.split(":", 1)[1] for tag in info.get("tags", []) if tag.startswith("license:")]
    return {"sha": info["sha"], "last_modified": info.get("lastModified"), "licenses": licenses}


def splits() -> dict[str, int]:
    query = urllib.parse.urlencode({"dataset": DATASET})
    size = _get(f"https://datasets-server.huggingface.co/size?{query}")
    return {split["split"]: split["num_rows"] for split in size["size"]["splits"]}


def rows(split: str, total: int) -> list[dict]:
    out = []
    for offset in range(0, total, PAGE):
        query = urllib.parse.urlencode(
            {"dataset": DATASET, "config": "default", "split": split, "offset": offset, "length": PAGE}
        )
        page = _get(f"https://datasets-server.huggingface.co/rows?{query}")
        out.extend(item["row"] for item in page["rows"])
    return out


def main() -> int:
    before = revision()
    counts = splits()
    written = {}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for split, total in counts.items():
        got = rows(split, total)
        written[split] = len(got)
        lines += [json.dumps({"split": split, **row}, ensure_ascii=False) for row in got]
    after = revision()
    if before["sha"] != after["sha"]:
        print(f"revision changed during download: {before['sha']} -> {after['sha']}", file=sys.stderr)
        return 1
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    meta = {"dataset": DATASET, **before, "splits_expected": counts, "splits_written": written}
    META.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print(f"{len(lines)} rows -> {OUT.relative_to(ROOT).as_posix()} (revision {before['sha'][:8]})")
    return 0 if written == counts else 1


if __name__ == "__main__":
    raise SystemExit(main())
