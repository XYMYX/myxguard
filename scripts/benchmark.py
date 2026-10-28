#!/usr/bin/env python3
"""Report precision, recall, and false-positive rate for a JSONL dataset.

The default table is the regression report. ``--eval`` adds F1 and a
per-category table for the held-out set.

Example::

    python scripts/benchmark.py datasets/samples.jsonl
    python scripts/benchmark.py datasets/eval/heldout.jsonl --eval
    python scripts/benchmark.py datasets/samples.jsonl --threshold 25 --json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow ``python scripts/benchmark.py`` without an editable install.
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from myxguard.benchmark import evaluate, format_eval_report, format_report
from myxguard.ml import MLModelError, MLNotInstalled
from myxguard.scoring import ScanConfig


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Benchmark MyxGuard on a JSONL dataset.")
    parser.add_argument(
        "dataset",
        nargs="?",
        default=str(_ROOT / "datasets" / "samples.jsonl"),
        help="Path to a JSONL file (default: datasets/samples.jsonl)",
    )
    parser.add_argument(
        "--threshold",
        type=int,
        default=25,
        help="Score at or above this value counts as a detection (default: 25)",
    )
    parser.add_argument("--json", action="store_true", help="Print the report as JSON")
    parser.add_argument(
        "--eval",
        action="store_true",
        help="Held-out report with F1, per language and per category",
    )
    parser.add_argument(
        "--ml",
        action="store_true",
        help="Also score the same file with the optional ONNX classifier and print both",
    )
    args = parser.parse_args(argv)
    if args.threshold < 0:
        print("threshold must be 0 or greater.", file=sys.stderr)
        return 2
    try:
        rules = evaluate(args.dataset, threshold=args.threshold)
        ml_report = None
        if args.ml:
            ml_report = evaluate(
                args.dataset,
                threshold=args.threshold,
                config=ScanConfig(ml=True),
            )
    except (OSError, ValueError, MLNotInstalled, MLModelError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if args.json:
        payload: dict = {"rules": rules}
        if ml_report is not None:
            payload["rules_ml"] = ml_report
        print(json.dumps(payload if args.ml else rules, indent=2))
    elif args.ml:
        print("Rules only")
        print(format_eval_report(rules) if args.eval else format_report(rules))
        print("")
        print("Rules plus classifier")
        print(format_eval_report(ml_report) if args.eval else format_report(ml_report))
        print(_latency_line(rules, ml_report))
    elif args.eval:
        print(format_eval_report(rules))
    else:
        print(format_report(rules))
    return 0


def _latency_line(rules: dict, ml_report: dict) -> str:
    def _ms(value: object) -> str:
        if not isinstance(value, float):
            return "n/a"
        return f"{value:.1f} ms"

    return (
        "Latency per text on CPU: "
        f"rules mean {_ms(rules.get('latency_ms_mean'))} "
        f"median {_ms(rules.get('latency_ms_median'))}, "
        f"rules+classifier mean {_ms(ml_report.get('latency_ms_mean'))} "
        f"median {_ms(ml_report.get('latency_ms_median'))}, "
        f"classifier call mean {_ms(ml_report.get('model_latency_ms_mean'))} "
        f"median {_ms(ml_report.get('model_latency_ms_median'))} "
        f"over {ml_report.get('model_calls')} calls."
    )


if __name__ == "__main__":
    raise SystemExit(main())
