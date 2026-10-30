"""Evaluation and report checks compute what they claim, on synthetic rows only.

These tests never read datasets/test_fresh/test_fresh.jsonl: looking at the
real scores before the final run would use the set up.
"""

import hashlib
import json

import pytest

from scripts.check_report_numbers import check_report
from scripts.eval_test_fresh import (
    THRESHOLD,
    coverage_gate,
    language_metrics,
    leakage_gate,
    score_rows,
    wilson,
)


def _row(label, category, note=None, language="de", text="t"):
    row = {"text": text, "label": label, "language": language, "category": category,
           "source": "synthetic", "license": "MIT"}
    if note:
        row["note"] = note
    return row


class _Result:
    def __init__(self, score):
        self.risk_score = score
        self.findings = []


def _fake_scan(scores):
    """A scan stand-in that returns the score stored under each text."""
    return lambda text: _Result(scores[text])


def _scored():
    rows = [
        _row("malicious", "instruction_override", text="io1"),
        _row("malicious", "instruction_override", text="io2"),
        _row("malicious", "data_exfiltration", text="ex1"),
        _row("malicious", "data_exfiltration", text="ex2"),
        _row("malicious", "jailbreak_persona", text="jp1"),
        _row("benign", "benign", "roleplay", text="b1"),
        _row("benign", "benign", "roleplay", text="b2"),
        _row("benign", "benign", "hard_negative", text="b3"),
        _row("benign", "benign", "plain", text="b4"),
        _row("malicious", "instruction_override", language="fr", text="other"),
    ]
    scores = {"io1": 80, "io2": 25, "ex1": 24, "ex2": 0, "jp1": 60,
              "b1": 30, "b2": 0, "b3": 0, "b4": 0, "other": 99}
    return score_rows(rows, _fake_scan(scores))


def test_threshold_is_fixed_at_25_and_inclusive():
    assert THRESHOLD == 25
    scored = {row["text"]: row["detected"] for row in _scored()}
    assert scored["io2"] is True and scored["ex1"] is False


def test_language_metrics_confusion_and_rates():
    metrics = language_metrics(_scored(), "de")
    assert metrics["confusion"] == {"tp": 3, "fn": 2, "fp": 1, "tn": 3}
    assert metrics["n"] == {"malicious": 5, "benign": 4}
    assert metrics["precision"] == pytest.approx(3 / 4)
    assert metrics["recall"] == pytest.approx(3 / 5)
    assert metrics["f1"] == pytest.approx(2 * 0.75 * 0.6 / 1.35)
    assert metrics["fpr"] == pytest.approx(1 / 4)


def test_category_metrics_are_one_vs_benign_of_the_same_language():
    by_category = language_metrics(_scored(), "de")["by_category"]
    exfil = by_category["data_exfiltration"]
    assert (exfil["tp"], exfil["fn"], exfil["fp"], exfil["tn"]) == (0, 2, 1, 3)
    assert exfil["recall"] == 0.0 and exfil["precision"] == 0.0
    override = by_category["instruction_override"]
    assert override["precision"] == pytest.approx(2 / 3)  # the fr row is not counted
    assert by_category["benign"]["fpr"] == pytest.approx(1 / 4)


def test_benign_subtype_false_alarm_rates():
    subtypes = language_metrics(_scored(), "de")["by_benign_subtype"]
    assert subtypes["roleplay"]["fp"] == 1 and subtypes["roleplay"]["fpr"] == pytest.approx(0.5)
    assert subtypes["hard_negative"]["fpr"] == 0.0


def test_by_source_splits_counts():
    by_source = language_metrics(_scored(), "de")["by_source"]
    assert by_source["synthetic"]["tp"] == 3 and by_source["synthetic"]["fp"] == 1


def test_every_error_is_listed_with_its_kind():
    metrics = language_metrics(_scored(), "de")
    kinds = sorted((error["kind"], error["text"]) for error in metrics["errors"])
    assert kinds == [("false_alarm", "b1"), ("missed", "ex1"), ("missed", "ex2")]
    assert metrics["error_count"] == 3


def test_empty_cells_give_none_not_zero():
    metrics = language_metrics(_scored(), "fr")
    assert metrics["fpr"] is None and metrics["precision"] == 1.0
    assert metrics["by_category"]["data_exfiltration"]["recall"] is None


def test_wilson_interval():
    low, high = wilson(5, 10)
    assert low == pytest.approx(0.2366, abs=1e-3) and high == pytest.approx(0.7634, abs=1e-3)
    assert wilson(0, 10)[0] == 0.0
    assert wilson(0, 0) is None


def test_leakage_gate(tmp_path):
    data = tmp_path / "test_fresh.jsonl"
    data.write_text('{"text": "x"}\n', encoding="utf-8")
    digest = hashlib.sha256(data.read_bytes()).hexdigest()
    report = tmp_path / "leak.json"

    assert leakage_gate(data, report)  # missing report
    report.write_text(json.dumps({"checked": {"x": digest}, "rows_checked": 1, "hits": []}), encoding="utf-8")
    assert leakage_gate(data, report) == []
    report.write_text(json.dumps({"checked": {"x": "0" * 64}, "rows_checked": 1, "hits": []}), encoding="utf-8")
    assert leakage_gate(data, report)  # report is for another version of the file
    report.write_text(json.dumps({"checked": {"x": digest}, "rows_checked": 1, "hits": [{"text": "x"}]}), encoding="utf-8")
    assert leakage_gate(data, report)  # hits


def test_coverage_gate_refuses_partial_set():
    english_attacks_only = [_row("malicious", "instruction_override", language="en")]
    assert len(coverage_gate(english_attacks_only)) == 7
    complete = [_row(label, category, note, language=language)
                for language in ("de", "en", "fr", "it")
                for label, category, note in (("malicious", "jailbreak_persona", None), ("benign", "benign", "plain"))]
    assert coverage_gate(complete) == []


def test_report_numbers_must_come_from_raw_json(tmp_path):
    raw = {"language": "de", "data_sha256": "ab" * 32,
           "n": {"malicious": 5, "benign": 4}, "precision": 0.75, "recall": 0.6, "fpr": 0.25}
    (tmp_path / "eval_de.json").write_text(json.dumps(raw), encoding="utf-8")
    good = tmp_path / "good.md"
    good.write_text(
        f"Set sha256 {'ab' * 32}\n\n| lang | n mal | n ben | P | R | FPR (CI 95 %) |\n|---|---|---|---|---|---|\n"
        "| de | 5 | 4 | 0.750 | 60.0 % | 25.0 % |\n",
        encoding="utf-8",
    )
    assert check_report(good, [tmp_path / "eval_de.json"]) == []
    bad = tmp_path / "bad.md"
    bad.write_text(good.read_text(encoding="utf-8").replace("60.0 %", "66.0 %"), encoding="utf-8")
    problems = check_report(bad, [tmp_path / "eval_de.json"])
    assert problems and "66.0" in problems[0]
    no_sha = tmp_path / "no_sha.md"
    no_sha.write_text("| de | 0.750 |\n", encoding="utf-8")
    assert check_report(no_sha, [tmp_path / "eval_de.json"])
