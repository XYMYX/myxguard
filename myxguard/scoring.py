"""Turn a list of findings into one score from 0 to 100.

The weights are easy to say out loud:

* one low finding stays in the "low" band (under 25)
* one medium finding reaches "medium" (25 to 49)
* one high finding reaches "high" (50 to 74)
* one critical finding reaches "critical" (75 to 100)

A second finding in a category that was already counted adds only a third of
its weight. Otherwise a page that repeats the same sentence would jump to 100.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from myxguard.models import Finding

WEIGHTS = {
    "low": 10,
    "medium": 25,
    "high": 55,
    "critical": 80,
}

_RANK = {
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}


def severity_rank(severity: str) -> int:
    try:
        return _RANK[severity]
    except KeyError as exc:
        raise ValueError(f"Unknown severity {severity!r}.") from exc


def risk_level(score: int) -> str:
    """Map a 0..100 score to the level name shown in reports."""
    if score <= 0:
        return "none"
    if score < 25:
        return "low"
    if score < 50:
        return "medium"
    if score < 75:
        return "high"
    return "critical"


@dataclass(frozen=True)
class ScanConfig:
    """Optional knobs for :func:`myxguard.scan`.

    Leaving this off keeps the rules-only behaviour: the weights above, an
    intent window of 18 tokens, and a detection cutoff of 25 (the bottom of
    ``medium``). ``scan`` still returns the raw score. Callers compare that
    score with ``detection_threshold`` the same way the benchmark does.

    ``ml=True`` runs the optional ONNX classifier when the rule score is
    below ``ml_short_circuit``. A clear high rule hit skips the model.
    """

    weights: Optional[dict[str, int]] = None
    intent_window: int = 18
    detection_threshold: int = 25
    ml: bool = False
    ml_model_path: Optional[str] = None
    ml_rule_weight: float = 0.5
    ml_model_weight: float = 0.5
    ml_short_circuit: int = 50

    def resolved_weights(self) -> dict[str, int]:
        """Return ``weights`` or the built-in table, after checking the keys."""
        table = WEIGHTS if self.weights is None else self.weights
        missing = [name for name in WEIGHTS if name not in table]
        if missing:
            raise ValueError(
                "weights must include low, medium, high, and critical. "
                f"Missing {', '.join(missing)}."
            )
        for name, value in table.items():
            if name not in WEIGHTS:
                raise ValueError(f"Unknown severity {name!r} in weights.")
            if not isinstance(value, int) or value < 0:
                raise ValueError(f"Weight for {name} must be a non-negative integer.")
        if self.intent_window < 2:
            raise ValueError("intent_window must be at least 2.")
        if self.detection_threshold < 0:
            raise ValueError("detection_threshold must be 0 or greater.")
        return {name: int(table[name]) for name in WEIGHTS}

    def check_ml(self) -> None:
        """Raise ``ValueError`` when the classifier knobs are unusable."""
        if self.ml_rule_weight < 0 or self.ml_model_weight < 0:
            raise ValueError("ML weights must be 0 or greater.")
        if self.ml_rule_weight + self.ml_model_weight <= 0:
            raise ValueError("At least one ML weight must be greater than 0.")
        if self.ml_short_circuit < 0:
            raise ValueError("ml_short_circuit must be 0 or greater.")


def combine_rule_and_model(
    rule_score: int,
    probability: float,
    rule_weight: float = 0.5,
    model_weight: float = 0.5,
) -> int:
    """Blend a rule score with a classifier probability, then keep the higher.

    ``probability`` is the model's chance that the text is an injection,
    from 0 to 1. It is turned into points from 0 to 100, mixed with the
    rule score using the two weights, and rounded. The rule score is kept
    when it is already higher, so the classifier cannot hide a rule hit.
    """
    if probability < 0 or probability > 1:
        raise ValueError("probability must be between 0 and 1.")
    if rule_weight < 0 or model_weight < 0 or rule_weight + model_weight <= 0:
        raise ValueError("ML weights must be 0 or greater, and not both 0.")
    model_points = probability * 100.0
    total = rule_weight + model_weight
    blended = (rule_weight * rule_score + model_weight * model_points) / total
    rounded = int(round(blended))
    if rounded < 0:
        rounded = 0
    if rounded > 100:
        rounded = 100
    if rule_score > rounded:
        return rule_score
    return rounded


def risk_score(
    findings: list[Finding],
    weights: Optional[dict[str, int]] = None,
) -> int:
    """Sum finding weights, then cap the result at 100."""
    table = WEIGHTS if weights is None else weights
    ordered = sorted(findings, key=lambda finding: table[finding.severity], reverse=True)
    seen_categories: set[str] = set()
    total = 0
    for finding in ordered:
        weight = table[finding.severity]
        if finding.category in seen_categories:
            weight = max(1, weight // 3)
        else:
            seen_categories.add(finding.category)
        total += weight
    if total > 100:
        return 100
    if total < 0:
        return 0
    return total
