"""The training corpus stays inside its license and away from held-out text."""

import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

from training.data import prepare
from training.dedupe import NearDupIndex

ROOT = Path(__file__).resolve().parents[1]
TRAIN = ROOT / "datasets" / "train" / "train.jsonl"
HELDOUT = ROOT / "datasets" / "eval" / "heldout.jsonl"
DEV = ROOT / "datasets" / "dev" / "dev.jsonl"
SAMPLES = ROOT / "datasets" / "samples.jsonl"
ALLOWED = {"MIT", "Apache-2.0", "CC-BY-4.0", "CC-BY-2.0-FR", "CC0-1.0"}
HARD_NEGATIVES = {
    "everyday",
    "email",
    "support",
    "recipe",
    "code",
    "code_comment",
    "log",
    "base64_image",
    "security_discussion",
    "ignore_previous_email",
}


def _rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_train_corpus_shape_and_balance():
    rows = _rows(TRAIN)
    assert 2000 <= len(rows) <= 3000
    labels = Counter(row["label"] for row in rows)
    assert labels["benign"] / len(rows) > 0.4
    assert labels["malicious"] / len(rows) > 0.4
    languages = Counter(row["language"] for row in rows)
    for language in ("en", "de", "fr", "it", "gsw"):
        assert languages[language] >= 400
    for row in rows:
        assert set(row) == {"text", "label", "language", "category", "source", "license"}
        assert row["label"] in {"malicious", "benign"}
        assert row["license"] in ALLOWED
        assert row["text"].strip()


def test_hard_negatives_cover_de_fr_it_gsw():
    rows = _rows(TRAIN)
    counts = Counter((row["language"], row["category"]) for row in rows if row["label"] == "benign")
    for language in ("de", "fr", "it", "gsw"):
        for category in HARD_NEGATIVES:
            assert counts[(language, category)] >= 12


def test_train_corpus_is_disjoint_from_heldout_and_dev():
    rows = _rows(TRAIN)
    heldout = NearDupIndex(row["text"] for row in _rows(HELDOUT))
    dev = NearDupIndex(row["text"] for row in _rows(DEV))
    sample_text = {row["text"] for row in _rows(SAMPLES)}
    for row in rows:
        assert not heldout.blocks(row["text"])
        assert not dev.blocks(row["text"])
        assert row["text"] not in sample_text


def test_prepare_drops_a_near_duplicate_of_heldout(tmp_path: Path):
    original = next(row["text"] for row in _rows(HELDOUT) if len(row["text"]) > 160)
    tweaked = original[:-1] + ("!" if not original.endswith("!") else "?")
    fresh = "The bakery on the corner sells rye bread on Tuesdays."
    train = tmp_path / "train.jsonl"
    train.write_text(
        json.dumps({"text": tweaked, "label": "benign"})
        + "\n"
        + json.dumps({"text": fresh, "label": "benign"})
        + "\n",
        encoding="utf-8",
    )
    rows = prepare([train], exclude=HELDOUT, augment=False)
    texts = {row["text"] for row in rows}
    assert tweaked not in texts
    assert fresh in texts


def test_prepare_keeps_dev_out_of_training(tmp_path: Path):
    dev_text = _rows(DEV)[0]["text"]
    train = tmp_path / "train.jsonl"
    fresh = "The bakery on the corner sells rye bread on Tuesdays."
    train.write_text(
        json.dumps({"text": dev_text, "label": "benign"})
        + "\n"
        + json.dumps({"text": fresh, "label": "benign"})
        + "\n",
        encoding="utf-8",
    )
    rows = prepare([train], exclude=None, block_paths=[DEV], augment=False)
    texts = {row["text"] for row in rows}
    assert dev_text not in texts
    assert fresh in texts


def test_dataset_stats_script():
    completed = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "dataset_stats.py"), str(TRAIN)],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "language" in completed.stdout
    assert "gsw:" in completed.stdout
    assert "label" in completed.stdout
    assert "category" in completed.stdout
    assert "tatoeba.org:" in completed.stdout
