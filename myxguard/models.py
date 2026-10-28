"""Result types returned by :func:`myxguard.scan`.

A finding always points at the original string: ``start`` and ``end`` are
offsets into that string, and ``span`` is the text between them (clipped when
it is very long). ``language`` is the pack that produced the finding, or
``None`` for detectors that are not tied to a language.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Optional

# Kept as plain strings so JSON output stays obvious for new contributors.
SEVERITIES = ("low", "medium", "high", "critical")
RISK_LEVELS = ("none", "low", "medium", "high", "critical")
CONTENT_TYPES = ("text", "html", "auto")

# Long Base64 blobs are real matches, but they do not need to fill a report.
MAX_SPAN_CHARS = 240


def clip_span(span: str) -> str:
    """Shorten a matched span for display without changing its offsets."""
    if len(span) <= MAX_SPAN_CHARS:
        return span
    return span[: MAX_SPAN_CHARS - 3] + "..."


@dataclass(frozen=True)
class Finding:
    """One place in the text that a detector was unhappy about."""

    rule_id: str
    category: str
    severity: str
    span: str
    start: int
    end: int
    explanation: str
    language: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "category": self.category,
            "severity": self.severity,
            "span": self.span,
            "start": self.start,
            "end": self.end,
            "explanation": self.explanation,
            "language": self.language,
        }


@dataclass(frozen=True)
class ScanResult:
    """The outcome of scanning one string."""

    risk_score: int
    risk_level: str
    findings: list[Finding]
    content_type: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "risk_score": self.risk_score,
            "risk_level": self.risk_level,
            "content_type": self.content_type,
            "findings": [finding.to_dict() for finding in self.findings],
        }

    def to_json(self, *, indent: Optional[int] = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


def make_finding(
    text: str,
    start: int,
    end: int,
    *,
    rule_id: str,
    category: str,
    severity: str,
    explanation: str,
    language: Optional[str] = None,
) -> Finding:
    """Build a finding and fill ``span`` from ``text[start:end]``."""
    if severity not in SEVERITIES:
        raise ValueError(f"Unknown severity {severity!r}. Expected one of {SEVERITIES}.")
    if start < 0:
        start = 0
    if end > len(text):
        end = len(text)
    if end < start:
        end = start
    return Finding(
        rule_id=rule_id,
        category=category,
        severity=severity,
        span=clip_span(text[start:end]),
        start=start,
        end=end,
        explanation=explanation,
        language=language,
    )
