#!/usr/bin/env python3
"""Evaluate the XLM-R classifier from ../apertus/xlmr-detector on test_fresh.

Same metrics, gates and output layout as ``eval_test_fresh.py``. Decision
rule: argmax over the two logits (label 1 = injection), the model's default
cut-off and the one used for the DEVLOG numbers. No threshold is chosen on
this set. ``score`` is P(injection) in percent, rounded to one decimal.
Needs torch and transformers; run with the interpreter of ../apertus/.venv.
The leakage report must also cover the XLM-R training data (``--block``).

Example::

    ../apertus/.venv/Scripts/python.exe scripts/eval_test_fresh_xlmr.py \
        --leakage-report reports/leakage_xlmr_2026-10-30.json
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.check_schema import LANGUAGES  # noqa: E402
from scripts.eval_test_fresh import DATA, OUT_DIR, coverage_gate, language_metrics, leakage_gate  # noqa: E402

MODEL = ROOT.parent / "apertus" / "xlmr-detector"
MAX_LENGTH = 256
BATCH = 32


def rows_from_predictions(rows: list[dict], probabilities: list[float], predictions: list[int]) -> list[dict]:
    """Scored rows in the shape ``language_metrics`` expects."""
    return [
        {**row, "row": index, "score": round(probability * 100, 1), "rules": [], "detected": prediction == 1}
        for index, (row, probability, prediction) in enumerate(zip(rows, probabilities, predictions), 1)
    ]


def predict(texts: list[str]) -> tuple[list[float], list[int]]:
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    device = "cuda" if torch.cuda.is_available() else "cpu"
    tokenizer = AutoTokenizer.from_pretrained(MODEL)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL).to(device).eval()
    probabilities, predictions = [], []
    for start in range(0, len(texts), BATCH):
        batch = tokenizer(texts[start:start + BATCH], truncation=True, max_length=MAX_LENGTH,
                          padding=True, return_tensors="pt").to(device)
        with torch.no_grad():
            logits = model(**batch).logits
        probabilities += torch.softmax(logits, -1)[:, 1].tolist()
        predictions += logits.argmax(-1).tolist()
    return probabilities, predictions


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main(argv: list[str] | None = None) -> int:
    sys.stdout.reconfigure(errors="replace")
    parser = argparse.ArgumentParser(description="Evaluate XLM-R on test_fresh per language.")
    parser.add_argument("--data", type=Path, default=DATA)
    parser.add_argument("--leakage-report", type=Path, required=True,
                        help="Leakage report that also blocked the XLM-R training data")
    args = parser.parse_args(argv)

    rows = [json.loads(line) for line in args.data.read_text(encoding="utf-8").splitlines() if line.strip()]
    problems = leakage_gate(args.data, args.leakage_report) + coverage_gate(rows)
    if problems:
        for problem in problems:
            print(f"refused: {problem}", file=sys.stderr)
        return 1

    import torch
    import transformers

    probabilities, predictions = predict([row["text"] for row in rows])
    scored = rows_from_predictions(rows, probabilities, predictions)
    today = datetime.date.today().isoformat()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for language in sorted(LANGUAGES):
        metrics = language_metrics(scored, language)
        payload = {
            "detector": "XLM-R classifier ../apertus/xlmr-detector, argmax",
            "model_sha256": _sha256(MODEL / "model.safetensors"),
            "torch_version": torch.__version__,
            "transformers_version": transformers.__version__,
            "device": "cuda" if torch.cuda.is_available() else "cpu",
            "max_length": MAX_LENGTH,
            "data": args.data.resolve().relative_to(ROOT).as_posix(),
            "data_sha256": hashlib.sha256(args.data.read_bytes()).hexdigest(),
            "leakage_report": args.leakage_report.resolve().relative_to(ROOT).as_posix(),
            "date": today,
            **metrics,
        }
        out = OUT_DIR / f"eval_xlmr_{language}_{today}.json"
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"{language}: n={metrics['n']} confusion={metrics['confusion']} errors={metrics['error_count']} -> {out.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
