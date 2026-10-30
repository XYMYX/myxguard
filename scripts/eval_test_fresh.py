#!/usr/bin/env python3
"""Evaluate MyxGuard (rules only) on datasets/test_fresh, one language per run.

Refuses to run unless the leakage report names the current SHA-256 of the
data file and lists zero hits. The threshold is fixed at 25 and cannot be
changed from the command line, so it cannot be tuned on the test set.

Per language: confusion matrix, precision, recall, F1, false-alarm rate on
benign rows; per category the same, one-vs-benign (rows of that category plus
all benign rows of the language); false-alarm rate per benign subtype; Wilson
95 % intervals; every error with its score and rule ids.

Run the four languages in parallel if you like; each writes its own file::

    python scripts/eval_test_fresh.py --lang de
    python scripts/eval_test_fresh.py --lang all
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Callable, Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.check_schema import ATTACK_CATEGORIES, BENIGN_SUBTYPES, LANGUAGES  # noqa: E402

DATA = ROOT / "datasets" / "test_fresh" / "test_fresh.jsonl"
OUT_DIR = ROOT / "reports" / "raw"
THRESHOLD = 25
Z95 = 1.959963984540054


def _ratio(num: int, den: int) -> Optional[float]:
    return num / den if den else None


def _f1(precision: Optional[float], recall: Optional[float]) -> Optional[float]:
    if precision is None or recall is None:
        return None
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def wilson(successes: int, total: int) -> Optional[list[float]]:
    """Wilson score interval, 95 %. None when there is nothing to estimate."""
    if total == 0:
        return None
    p = successes / total
    denom = 1 + Z95**2 / total
    centre = (p + Z95**2 / (2 * total)) / denom
    half = Z95 * math.sqrt(p * (1 - p) / total + Z95**2 / (4 * total**2)) / denom
    return [max(0.0, centre - half), min(1.0, centre + half)]


def score_rows(rows: list[dict], scan_fn: Callable[[str], object]) -> list[dict]:
    """Attach score, rule ids and the detection decision to every row."""
    scored = []
    for index, row in enumerate(rows, 1):
        result = scan_fn(row["text"])
        scored.append({
            **row,
            "row": index,
            "score": result.risk_score,
            "rules": sorted({finding.rule_id for finding in result.findings}),
            "detected": result.risk_score >= THRESHOLD,
        })
    return scored


def _confusion(attacks: list[dict], benign: list[dict]) -> dict:
    tp = sum(row["detected"] for row in attacks)
    fp = sum(row["detected"] for row in benign)
    return {"tp": tp, "fn": len(attacks) - tp, "fp": fp, "tn": len(benign) - fp}


def _rates(confusion: dict) -> dict:
    tp, fn, fp, tn = (confusion[key] for key in ("tp", "fn", "fp", "tn"))
    precision = _ratio(tp, tp + fp)
    recall = _ratio(tp, tp + fn)
    return {
        "precision": precision,
        "recall": recall,
        "f1": _f1(precision, recall),
        "fpr": _ratio(fp, fp + tn),
        "recall_ci95": wilson(tp, tp + fn),
        "fpr_ci95": wilson(fp, fp + tn),
    }


def language_metrics(scored: list[dict], language: str) -> dict:
    rows = [row for row in scored if row["language"] == language]
    attacks = [row for row in rows if row["label"] == "malicious"]
    benign = [row for row in rows if row["label"] == "benign"]
    confusion = _confusion(attacks, benign)

    by_category = {}
    for category in sorted(ATTACK_CATEGORIES):
        cat_confusion = _confusion([row for row in attacks if row["category"] == category], benign)
        by_category[category] = {"n": cat_confusion["tp"] + cat_confusion["fn"], **cat_confusion, **_rates(cat_confusion)}
    fp = confusion["fp"]
    by_category["benign"] = {"n": len(benign), "fp": fp, "tn": len(benign) - fp,
                             "fpr": _ratio(fp, len(benign)), "fpr_ci95": wilson(fp, len(benign))}

    by_subtype = {}
    for subtype in sorted(BENIGN_SUBTYPES):
        group = [row for row in benign if row.get("note") == subtype]
        sub_fp = sum(row["detected"] for row in group)
        by_subtype[subtype] = {"n": len(group), "fp": sub_fp, "fpr": _ratio(sub_fp, len(group)),
                               "fpr_ci95": wilson(sub_fp, len(group))}

    errors = [
        {
            "kind": "missed" if row["label"] == "malicious" else "false_alarm",
            "row": row["row"],
            "category": row["category"],
            "note": row.get("note"),
            "source": row["source"],
            "score": row["score"],
            "rules": row["rules"],
            "text": row["text"],
        }
        for row in rows
        if row["detected"] != (row["label"] == "malicious")
    ]
    return {
        "language": language,
        "n": {"malicious": len(attacks), "benign": len(benign)},
        "confusion": confusion,
        **_rates(confusion),
        "by_category": by_category,
        "by_benign_subtype": by_subtype,
        "error_count": len(errors),
        "errors": errors,
        "scores": [{"row": row["row"], "label": row["label"], "category": row["category"],
                    "note": row.get("note"), "score": row["score"], "detected": row["detected"]} for row in rows],
    }


def leakage_gate(data: Path, report: Path) -> list[str]:
    """Problems that forbid an evaluation; empty list means the gate is open."""
    if not report.is_file():
        return [f"leakage report missing: {report}"]
    leak = json.loads(report.read_text(encoding="utf-8"))
    digest = hashlib.sha256(data.read_bytes()).hexdigest()
    problems = []
    if digest not in leak.get("checked", {}).values():
        problems.append(f"leakage report does not cover the current file (sha256 {digest[:12]})")
    if leak.get("hits"):
        problems.append(f"leakage report has {len(leak['hits'])} hits")
    if not leak.get("rows_checked"):
        problems.append("leakage report checked 0 rows")
    return problems


def coverage_gate(rows: list[dict]) -> list[str]:
    """The set is evaluated once, when complete: every language needs both labels."""
    present = {(row["language"], row["label"]) for row in rows}
    return [
        f"{language} has no {label} rows; no evaluation on a partial set"
        for language in sorted(LANGUAGES)
        for label in ("malicious", "benign")
        if (language, label) not in present
    ]


def _latest_leakage_report() -> Path:
    reports = sorted((ROOT / "reports").glob("leakage_*.json"))
    return reports[-1] if reports else ROOT / "reports" / "leakage_missing.json"


def main(argv: list[str] | None = None) -> int:
    sys.stdout.reconfigure(errors="replace")
    parser = argparse.ArgumentParser(description="Evaluate MyxGuard on test_fresh per language.")
    parser.add_argument("--lang", required=True, choices=sorted(LANGUAGES) + ["all"])
    parser.add_argument("--data", type=Path, default=DATA)
    parser.add_argument("--leakage-report", type=Path, help="Default: newest reports/leakage_*.json")
    args = parser.parse_args(argv)

    leakage_report = args.leakage_report or _latest_leakage_report()
    rows = [json.loads(line) for line in args.data.read_text(encoding="utf-8").splitlines() if line.strip()]
    problems = leakage_gate(args.data, leakage_report) + coverage_gate(rows)
    if problems:
        for problem in problems:
            print(f"refused: {problem}", file=sys.stderr)
        return 1

    import myxguard
    from myxguard.scanner import scan

    languages = sorted(LANGUAGES) if args.lang == "all" else [args.lang]
    scored = [row for row in score_rows(rows, scan) if row["language"] in languages]

    today = datetime.date.today().isoformat()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for language in languages:
        metrics = language_metrics(scored, language)
        payload = {
            "detector": "myxguard.scan, rules only",
            "myxguard_version": myxguard.__version__,
            "threshold": THRESHOLD,
            "data": args.data.resolve().relative_to(ROOT).as_posix() if args.data.resolve().is_relative_to(ROOT) else str(args.data),
            "data_sha256": hashlib.sha256(args.data.read_bytes()).hexdigest(),
            "leakage_report": leakage_report.resolve().relative_to(ROOT).as_posix(),
            "date": today,
            **metrics,
        }
        out = OUT_DIR / f"eval_{language}_{today}.json"
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"{language}: n={metrics['n']} confusion={metrics['confusion']} errors={metrics['error_count']} -> {out.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
