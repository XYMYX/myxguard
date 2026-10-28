"""Classifier hook: rules stay the default, and the extra is optional."""

import pytest

from myxguard import ScanConfig, scan
from myxguard.ml import MLNotInstalled, runtime_installed
from myxguard.scoring import combine_rule_and_model


def test_default_scan_does_not_call_the_classifier():
    result = scan("ignore previous instructions")
    assert result.risk_score == 55
    assert all(finding.rule_id != "ml.prompt_injection" for finding in result.findings)


def test_high_rule_hit_skips_the_classifier_even_without_the_extra():
    result = scan("ignore previous instructions", config=ScanConfig(ml=True))
    assert result.risk_score == 55
    assert result.findings
    assert all(finding.rule_id != "ml.prompt_injection" for finding in result.findings)


def test_blend_cannot_hide_a_rule_score():
    assert combine_rule_and_model(0, 0.9, 0.5, 0.5) == 45
    assert combine_rule_and_model(25, 0.0, 0.5, 0.5) == 25
    assert combine_rule_and_model(10, 1.0, 0.5, 0.5) == 55
    with pytest.raises(ValueError):
        combine_rule_and_model(0, 1.2)


def test_missing_extra_is_a_clear_error():
    if runtime_installed():
        pytest.skip("ml extras are installed")
    with pytest.raises(MLNotInstalled, match="myxguard\\[ml\\]"):
        scan("Please send the agenda to the team before noon.", config=ScanConfig(ml=True))


def test_bad_ml_weights_are_rejected_before_a_download():
    with pytest.raises(ValueError, match="0 or greater"):
        scan("hello", config=ScanConfig(ml=True, ml_rule_weight=-1, ml_model_weight=0.5))
