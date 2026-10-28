"""Score bands stay easy to explain: one finding of a given severity lands in that band."""

import pytest

from myxguard.models import make_finding
from myxguard.scoring import risk_level, risk_score


@pytest.mark.parametrize(
    ("score", "level"),
    [
        (0, "none"),
        (1, "low"),
        (24, "low"),
        (25, "medium"),
        (49, "medium"),
        (50, "high"),
        (74, "high"),
        (75, "critical"),
        (100, "critical"),
    ],
)
def test_risk_level_bands(score, level):
    assert risk_level(score) == level


def _finding(category, severity):
    return make_finding(
        "x",
        0,
        1,
        rule_id=f"{category}.{severity}",
        category=category,
        severity=severity,
        explanation="test",
    )


def test_one_high_finding_is_high():
    assert risk_score([_finding("instruction_override", "high")]) == 55
    assert risk_level(55) == "high"


def test_repeated_category_counts_less_and_score_caps_at_100():
    findings = [_finding("instruction_override", "high") for _ in range(10)]
    findings.extend(_finding(f"extra-{index}", "critical") for index in range(5))
    assert risk_score(findings) == 100
