"""Score a JSONL dataset and report precision, recall, and false-positive rate.

Each line needs ``text``, ``label`` (``malicious`` or ``benign``), ``language``,
``category``, and ``source``. A row is counted as a detection when its risk
score is greater than or equal to ``threshold``. The default threshold is 25,
which is the bottom of the "medium" band: a lone low finding does not count.

``format_report`` is the regression table (precision, recall, false-positive
rate per language). ``format_eval_report`` is the held-out table: the same
rates plus F1, once per language and once per category. The eval set is not
used to change rules.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Iterable, Optional, Sequence

from myxguard import ml as ml_runtime
from myxguard.scanner import scan
from myxguard.scoring import ScanConfig

REQUIRED_FIELDS = ("text", "label", "language", "category", "source")
LABELS = ("malicious", "benign")


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    """Read a dataset file and check that every row has the expected fields."""
    rows: list[dict[str, Any]] = []
    file_path = Path(path)
    with file_path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{file_path}:{line_number} is not valid JSON.") from exc
            missing = [field for field in REQUIRED_FIELDS if field not in row]
            if missing:
                raise ValueError(f"{file_path}:{line_number} is missing {', '.join(missing)}.")
            if row["label"] not in LABELS:
                raise ValueError(
                    f"{file_path}:{line_number} has label {row['label']!r}. "
                    "Use 'malicious' or 'benign'."
                )
            if not isinstance(row["text"], str):
                raise ValueError(f"{file_path}:{line_number} text must be a string.")
            rows.append(row)
    if not rows:
        raise ValueError(f"{file_path} has no rows.")
    return rows


def evaluate(
    path: str | Path,
    *,
    threshold: int = 25,
    languages: Optional[Sequence[str]] = None,
    config: Optional[ScanConfig] = None,
) -> dict[str, Any]:
    """Scan every row and compute rates per language and overall.

    ``config`` is how the rules+classifier run is selected. The default
    ``None`` is rules only, and the plain-text regression report ignores
    the latency fields so older output stays stable.
    """
    if threshold < 0:
        raise ValueError("threshold must be 0 or greater.")
    scored = []
    elapsed_seconds = []
    model_seconds = []
    for row in load_jsonl(path):
        started = time.perf_counter()
        result = scan(row["text"], languages=languages, config=config)
        elapsed_seconds.append(time.perf_counter() - started)
        used_model = any(finding.rule_id == "ml.prompt_injection" for finding in result.findings)
        if used_model and ml_runtime.last_predict_seconds is not None:
            model_seconds.append(ml_runtime.last_predict_seconds)
        scored.append(
            {
                "language": row["language"],
                "label": row["label"],
                "category": row["category"],
                "score": result.risk_score,
                "level": result.risk_level,
                "detected": result.risk_score >= threshold,
            }
        )
    languages_in_file = []
    for row in scored:
        if row["language"] not in languages_in_file:
            languages_in_file.append(row["language"])
    categories = sorted({row["category"] for row in scored})
    by_language = {language: _rates(scored, language) for language in languages_in_file}
    by_category = {category: _rates(scored, category=category) for category in categories}
    return {
        "path": str(path),
        "threshold": threshold,
        "rows": len(scored),
        "by_language": by_language,
        "by_category": by_category,
        "overall": _rates(scored, None),
        "latency_ms_mean": _mean_ms(elapsed_seconds),
        "latency_ms_median": _median_ms(elapsed_seconds),
        "model_latency_ms_mean": _mean_ms(model_seconds),
        "model_latency_ms_median": _median_ms(model_seconds),
        "model_calls": len(model_seconds),
        "ml": bool(config is not None and config.ml),
    }


def _rates(
    rows: Iterable[dict[str, Any]],
    language: Optional[str] = None,
    category: Optional[str] = None,
) -> dict[str, Any]:
    chosen = [
        row
        for row in rows
        if (language is None or row["language"] == language)
        and (category is None or row["category"] == category)
    ]
    true_positive = false_positive = true_negative = false_negative = 0
    for row in chosen:
        malicious = row["label"] == "malicious"
        if row["detected"] and malicious:
            true_positive += 1
        elif row["detected"] and not malicious:
            false_positive += 1
        elif not row["detected"] and not malicious:
            true_negative += 1
        else:
            false_negative += 1
    predicted = true_positive + false_positive
    malicious_count = true_positive + false_negative
    benign_count = false_positive + true_negative
    precision = _div(true_positive, predicted)
    recall = _div(true_positive, malicious_count)
    return {
        "support": len(chosen),
        "malicious": malicious_count,
        "benign": benign_count,
        "tp": true_positive,
        "fp": false_positive,
        "tn": true_negative,
        "fn": false_negative,
        "precision": precision,
        "recall": recall,
        "f1": _f1(precision, recall),
        "fpr": _div(false_positive, benign_count),
    }


def _f1(precision: Optional[float], recall: Optional[float]) -> Optional[float]:
    """Harmonic mean. ``None`` when precision or recall has no denominator."""
    if precision is None or recall is None:
        return None
    if precision + recall == 0:
        return 0.0
    return (2 * precision * recall) / (precision + recall)


def _mean_ms(samples: list[float]) -> Optional[float]:
    if not samples:
        return None
    return (sum(samples) / len(samples)) * 1000.0


def _median_ms(samples: list[float]) -> Optional[float]:
    if not samples:
        return None
    ordered = sorted(samples)
    mid = len(ordered) // 2
    if len(ordered) % 2 == 1:
        return ordered[mid] * 1000.0
    return ((ordered[mid - 1] + ordered[mid]) / 2.0) * 1000.0


def _div(numerator: int, denominator: int) -> Optional[float]:
    if denominator == 0:
        return None
    return numerator / denominator


def format_report(report: dict[str, Any]) -> str:
    """Plain-text table for the command line."""
    lines = [
        "MyxGuard benchmark",
        f"file: {report['path']}",
        f"threshold: score >= {report['threshold']}",
        f"rows: {report['rows']}",
        "",
        f"{'language':<12} {'n':>5} {'mal':>5} {'ben':>5} {'tp':>4} {'fp':>4} "
        f"{'fn':>4} {'tn':>4} {'precision':>10} {'recall':>8} {'fpr':>8}",
    ]
    blocks = list(report["by_language"].items()) + [("ALL", report["overall"])]
    for language, rates in blocks:
        lines.append(
            f"{language:<12} {rates['support']:>5} {rates['malicious']:>5} "
            f"{rates['benign']:>5} {rates['tp']:>4} {rates['fp']:>4} {rates['fn']:>4} "
            f"{rates['tn']:>4} {_fmt(rates['precision']):>10} {_fmt(rates['recall']):>8} "
            f"{_fmt(rates['fpr']):>8}"
        )
    lines.append("")
    lines.append(
        "A row counts as detected when risk_score >= threshold. "
        "Precision is tp/(tp+fp), recall is tp/(tp+fn), false-positive rate is fp/(fp+tn)."
    )
    return "\n".join(lines)


def format_eval_report(report: dict[str, Any]) -> str:
    """Held-out report: precision, recall, F1, and false-positive rate.

    The language block matches the regression columns, plus F1. The category
    block uses the ``category`` field on each row (the label, not whichever
    rule the scanner happened to fire).
    """
    name = Path(str(report["path"])).name
    if name == "heldout.jsonl":
        split_line = "split: held-out (not used to write or tune rules)"
    else:
        split_line = f"split: {name}"
    lines = [
        "MyxGuard eval benchmark",
        f"file: {report['path']}",
        split_line,
        f"threshold: score >= {report['threshold']}",
        f"rows: {report['rows']}",
        "",
        "By language",
        _table_header("language", 12),
    ]
    blocks = list(report["by_language"].items()) + [("ALL", report["overall"])]
    for name, rates in blocks:
        lines.append(_table_row(name, 12, rates))
    lines.append("")
    lines.append("By category")
    lines.append(_table_header("category", 24))
    for name, rates in report["by_category"].items():
        lines.append(_table_row(name, 24, rates))
    lines.append("")
    lines.append(
        "A row counts as detected when risk_score >= threshold. "
        "Precision is tp/(tp+fp), recall is tp/(tp+fn), "
        "F1 is the harmonic mean of precision and recall, "
        "false-positive rate is fp/(fp+tn). n/a means the denominator was zero."
    )
    return "\n".join(lines)


def _table_header(name_column: str, width: int) -> str:
    return (
        f"{name_column:<{width}} {'n':>5} {'mal':>5} {'ben':>5} {'tp':>4} {'fp':>4} "
        f"{'fn':>4} {'tn':>4} {'precision':>10} {'recall':>8} {'f1':>8} {'fpr':>8}"
    )


def _table_row(name: str, width: int, rates: dict[str, Any]) -> str:
    return (
        f"{name:<{width}} {rates['support']:>5} {rates['malicious']:>5} "
        f"{rates['benign']:>5} {rates['tp']:>4} {rates['fp']:>4} {rates['fn']:>4} "
        f"{rates['tn']:>4} {_fmt(rates['precision']):>10} {_fmt(rates['recall']):>8} "
        f"{_fmt(rates['f1']):>8} {_fmt(rates['fpr']):>8}"
    )


def _fmt(value: Optional[float]) -> str:
    if value is None:
        return "n/a"
    return f"{value:.3f}"
