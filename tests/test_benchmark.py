"""The bundled dataset is a regression set: medium-and-above should be clean."""

from pathlib import Path

from myxguard.benchmark import evaluate, load_jsonl

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / "datasets" / "samples.jsonl"
DEEPSET = ROOT / "datasets" / "deepset_sample.jsonl"


def test_samples_separate_malicious_from_benign_at_medium():
    report = evaluate(SAMPLES, threshold=25)
    overall = report["overall"]
    assert overall["support"] >= 80
    assert overall["recall"] == 1
    assert overall["precision"] == 1
    assert overall["fpr"] == 0
    for language, rates in report["by_language"].items():
        assert rates["recall"] == 1, language
        assert rates["fpr"] == 0, language
        assert rates["malicious"] >= 4, language
        assert rates["benign"] >= 4, language


def test_dataset_rows_have_the_required_fields():
    rows = load_jsonl(SAMPLES)
    languages = {row["language"] for row in rows}
    assert languages == {"en", "de", "fr", "it", "gsw"}
    assert {row["label"] for row in rows} == {"malicious", "benign"}


def test_deepset_sample_is_attributed_and_separable():
    rows = load_jsonl(DEEPSET)
    assert rows
    assert all(row["source"] == "deepset/prompt-injections" for row in rows)
    report = evaluate(DEEPSET, threshold=25)
    assert report["overall"]["recall"] == 1
    assert report["overall"]["fpr"] == 0
