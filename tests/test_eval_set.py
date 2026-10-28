"""The held-out eval set stays separate from the regression set."""

import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

from myxguard.benchmark import evaluate, format_eval_report, format_report, load_jsonl

ROOT = Path(__file__).resolve().parents[1]
EVAL = ROOT / "datasets" / "eval" / "heldout.jsonl"
SAMPLES = ROOT / "datasets" / "samples.jsonl"
DEEPSET = ROOT / "datasets" / "deepset_sample.jsonl"
ALLOWED_LICENSES = {"MIT", "Apache-2.0", "CC-BY-2.0-FR", "CC-BY-4.0", "CC0-1.0"}


def test_eval_rows_are_balanced_licensed_and_held_out():
    rows = load_jsonl(EVAL)
    assert len(rows) >= 300
    languages = {row["language"] for row in rows}
    assert languages == {"en", "de", "fr", "it", "gsw"}
    labels = Counter(row["label"] for row in rows)
    assert labels["malicious"] >= 100
    assert labels["benign"] >= 100
    by_language = Counter(row["language"] for row in rows)
    for language, count in by_language.items():
        assert count >= 40, language
        in_language = [row for row in rows if row["language"] == language]
        malicious = sum(row["label"] == "malicious" for row in in_language)
        benign = count - malicious
        assert malicious >= 24 and benign >= 24, language
    for row in rows:
        assert row["source"]
        assert row["license"] in ALLOWED_LICENSES
        assert row["category"]
    regression = set()
    for path in (SAMPLES, DEEPSET):
        for row in load_jsonl(path):
            regression.add(row["text"])
    overlap = [row["text"][:80] for row in rows if row["text"] in regression]
    assert overlap == []


def test_eval_report_adds_f1_and_categories_without_changing_regression_text():
    report = evaluate(EVAL, threshold=25)
    assert "by_category" in report
    assert report["overall"]["f1"] is not None
    text = format_eval_report(report)
    assert "By language" in text
    assert "By category" in text
    assert "F1" in text
    # The regression wording stays stable for the README examples.
    sample = evaluate(SAMPLES, threshold=25)
    classic = format_report(sample)
    assert classic.startswith("MyxGuard benchmark\n")
    assert "F1" not in classic
    assert "false-positive rate is fp/(fp+tn)." in classic


def test_eval_cli_flag_prints_the_category_table():
    completed = subprocess.run(
        [sys.executable, "scripts/benchmark.py", "datasets/eval/heldout.jsonl", "--eval"],
        text=True,
        capture_output=True,
        check=False,
        cwd=ROOT,
    )
    assert completed.returncode == 0, completed.stderr
    assert "MyxGuard eval benchmark" in completed.stdout
    assert "By category" in completed.stdout
    payload = json.loads(
        subprocess.run(
            [
                sys.executable,
                "scripts/benchmark.py",
                "datasets/eval/heldout.jsonl",
                "--eval",
                "--json",
            ],
            text=True,
            capture_output=True,
            check=False,
            cwd=ROOT,
        ).stdout
    )
    assert "instruction_override" in payload["by_category"]
    assert "f1" in payload["overall"]


def test_windows_manual_has_cmd_examples():
    manual = (ROOT / "tests" / "manual_examples.md").read_text(encoding="utf-8")
    assert "cmd.exe" in manual
    assert "python -m myxguard check examples\\benign.txt --no-color" in manual
    assert "echo %ERRORLEVEL%" in manual
    assert "datasets\\eval\\heldout.jsonl --eval" in manual
