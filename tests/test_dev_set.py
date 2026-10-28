"""The dev set is original text, separate from the held-out eval file."""

import json
from pathlib import Path

from myxguard.benchmark import evaluate, load_jsonl

ROOT = Path(__file__).resolve().parents[1]
DEV = ROOT / "datasets" / "dev" / "dev.jsonl"
SAMPLES = ROOT / "datasets" / "samples.jsonl"
HELDOUT = ROOT / "datasets" / "eval" / "heldout.jsonl"


def test_dev_set_shape_and_license():
    rows = load_jsonl(DEV)
    assert len(rows) >= 100
    assert {row["language"] for row in rows} == {"en", "de", "fr", "it", "gsw"}
    assert {row["label"] for row in rows} == {"malicious", "benign"}
    for row in rows:
        assert row["source"] == "myxguard-dev-original"
        raw = json.loads(
            next(
                line
                for line in DEV.read_text(encoding="utf-8").splitlines()
                if json.loads(line)["text"] == row["text"]
            )
        )
        assert raw["license"] == "MIT"
    for language in ("en", "de", "fr", "it", "gsw"):
        group = [row for row in rows if row["language"] == language]
        assert sum(row["label"] == "malicious" for row in group) >= 8
        assert sum(row["label"] == "benign" for row in group) >= 8


def test_dev_set_does_not_copy_samples_or_heldout():
    dev = {row["text"] for row in load_jsonl(DEV)}
    samples = {row["text"] for row in load_jsonl(SAMPLES)}
    heldout = {row["text"] for row in load_jsonl(HELDOUT)}
    assert dev.isdisjoint(samples)
    assert dev.isdisjoint(heldout)


def test_dev_set_keeps_a_low_false_positive_rate():
    report = evaluate(DEV, threshold=25)
    overall = report["overall"]
    assert overall["recall"] >= 0.85
    assert overall["fpr"] <= 0.05
    assert overall["precision"] >= 0.9
    for language, rates in report["by_language"].items():
        assert rates["fpr"] <= 0.05, language
