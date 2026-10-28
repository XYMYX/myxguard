"""Glue the detectors together.

Pipeline for one string:

1. Decide whether it should be read as HTML.
2. Fold invisible characters so they cannot split a keyword, and remember
   the original offsets.
3. Turn ``\\xHH`` / ``\\uHHHH`` escapes into real characters, then run the
   phrase, transcript, and intent detectors on that text.
4. Run Unicode, obfuscation, and (for HTML) hidden-text detectors.
5. Drop an intent hit that only repeats a phrase hit, and drop a plain
   ``System`` / ``User`` / ``Assistant`` log that contains no instruction.
6. Drop duplicate hits, then downgrade phrases that are quoted in a write-up
   or that sit on a code-comment line.
7. Turn what is left into a score from 0 to 100.
"""

from __future__ import annotations

import re
from dataclasses import replace
from pathlib import Path
from typing import Optional, Sequence

from myxguard.context import apply_discussion_context
from myxguard.detectors.delimiters import scan_transcripts
from myxguard.detectors.html_hidden import scan_html
from myxguard.detectors.intent import scan_intent
from myxguard.detectors.obfuscation import scan_obfuscation
from myxguard.detectors.patterns import scan_patterns
from myxguard.detectors.unicode_hidden import TagPayload, scan_unicode
from myxguard.models import (
    CONTENT_TYPES,
    Finding,
    ScanResult,
    clip_span,
    make_finding,
)
from myxguard.ml import injection_probability, make_model_finding
from myxguard.scoring import (
    ScanConfig,
    combine_rule_and_model,
    risk_level,
    risk_score,
    severity_rank,
)
from myxguard.textutil import decode_inline_escapes, fold_text, map_piece_span, map_span

# Long pasted pages are scanned up to this size so one request cannot
# spend unbounded time in the regular expressions.
MAX_SCAN_CHARS = 500_000
_MAX_FINDINGS = 40

# A real tag (``<div``, ``<abbr title=...>``), or the start of a comment.
# ``a < b`` does not match, because a tag name has to follow the bracket.
_HTML_HINT = re.compile(r"(?i)(?:<!--|</?[a-z][a-z0-9:-]*\b)")


def scan(
    text: str,
    *,
    content_type: str = "auto",
    languages: Optional[Sequence[str]] = None,
    config: Optional[ScanConfig] = None,
) -> ScanResult:
    """Scan ``text`` and return a score, a level, and the findings.

    ``content_type`` is ``"text"``, ``"html"``, or ``"auto"``. ``"auto"``
    treats the input as HTML when it contains a real tag such as ``<div>``.
    ``languages`` limits the phrase packs. ``None`` uses every pack.
    German (``de``) also loads Swiss German (``gsw``).

    ``config`` is optional. Leave it off to keep the built-in weights and
    the intent window of 18 tokens. ``scan`` still returns the raw score;
    compare it with ``config.detection_threshold`` the way the benchmark does.
    """
    if not isinstance(text, str):
        raise TypeError("text must be a str.")
    active = config if config is not None else ScanConfig()
    weights = active.resolved_weights()
    if active.ml:
        active.check_ml()
    resolved = resolve_content_type(text, content_type)

    findings: list[Finding] = []
    if len(text) > MAX_SCAN_CHARS:
        text = text[:MAX_SCAN_CHARS]
        findings.append(
            make_finding(
                text,
                MAX_SCAN_CHARS - 1,
                MAX_SCAN_CHARS,
                rule_id="scanner.input_truncated",
                category="scanner",
                severity="low",
                explanation=(
                    f"Only the first {MAX_SCAN_CHARS} characters were scanned."
                ),
            )
        )

    folded, mapping = fold_text(text)
    decoded, piece_spans = decode_inline_escapes(folded)
    unicode_scan = scan_unicode(text)
    findings.extend(unicode_scan.findings)
    findings.extend(_tag_payload_findings(text, unicode_scan.tag_payloads, languages))
    # Phrases and intent see the decoded text, so ``Ignore\\x20all`` matches
    # the same way as ``Ignore all``. Obfuscation still sees the folded
    # source, where Base64 and hex runs are intact.
    findings.extend(
        _publish(scan_patterns(decoded, languages), text, mapping, piece_spans)
    )
    findings.extend(
        _publish(scan_transcripts(decoded), text, mapping, piece_spans)
    )
    findings.extend(
        _publish(
            scan_intent(decoded, languages, window=active.intent_window),
            text,
            mapping,
            piece_spans,
        )
    )
    findings.extend(_remap(scan_obfuscation(folded, languages), text, mapping))
    if resolved == "html":
        findings.extend(scan_html(text, languages))

    findings = _drop_shadowed_intent(findings)
    findings = _drop_plain_transcripts(findings)
    findings = _dedup(findings)
    findings = apply_discussion_context(text, findings)
    findings = _limit(findings)
    score = risk_score(findings, weights)
    # A high rule score is enough. Skip the classifier so a sure hit stays
    # fast and the optional model cannot talk it down. Below that line the
    # model may raise the score. The rule score is never lowered.
    if active.ml and score < active.ml_short_circuit and text.strip():
        probability = injection_probability(text, active.ml_model_path)
        findings = list(findings)
        findings.append(make_model_finding(text, probability))
        score = combine_rule_and_model(
            score,
            probability,
            active.ml_rule_weight,
            active.ml_model_weight,
        )
    return ScanResult(
        risk_score=score,
        risk_level=risk_level(score),
        findings=findings,
        content_type=resolved,
    )


def scan_file(
    path: str | Path,
    *,
    content_type: str = "auto",
    languages: Optional[Sequence[str]] = None,
    config: Optional[ScanConfig] = None,
) -> ScanResult:
    """Read a UTF-8 file and scan it.

    With ``content_type="auto"``, ``.html`` and ``.htm`` files are parsed
    as HTML even when the markup is unusual. Any other explicit content
    type is left as given.
    """
    file_path = Path(path)
    text = file_path.read_text(encoding="utf-8", errors="replace")
    if content_type == "auto" and file_path.suffix.lower() in {".html", ".htm"}:
        content_type = "html"
    return scan(text, content_type=content_type, languages=languages, config=config)


def resolve_content_type(text: str, content_type: str) -> str:
    """Return ``text`` or ``html`` after applying the ``auto`` rule."""
    if content_type not in CONTENT_TYPES:
        names = ", ".join(CONTENT_TYPES)
        raise ValueError(f"content_type must be one of {names}, not {content_type!r}.")
    if content_type != "auto":
        return content_type
    if _HTML_HINT.search(text):
        return "html"
    return "text"


def _tag_payload_findings(
    text: str,
    payloads: list[TagPayload],
    languages: Optional[Sequence[str]],
) -> list[Finding]:
    findings: list[Finding] = []
    for payload in payloads:
        inner = scan_patterns(payload.decoded, languages)
        preview = payload.decoded.replace("\n", " ")
        if len(preview) > 80:
            preview = preview[:77] + "..."
        if inner:
            top = max(inner, key=lambda finding: severity_rank(finding.severity))
            severity = "critical" if severity_rank(top.severity) >= severity_rank("high") else "high"
            explanation = (
                f"Unicode Tag characters hide ASCII text {preview!r}, "
                f"which matches {top.rule_id}."
            )
            rule_id = "unicode.tag.payload"
        else:
            severity = "high"
            rule_id = "unicode.tag.hidden_ascii"
            explanation = (
                f"Unicode Tag characters hide ASCII text {preview!r}. "
                "It does not match a known phrase, but tag characters do not "
                "belong in a normal prompt."
            )
        findings.append(
            make_finding(
                text,
                payload.start,
                payload.end,
                rule_id=rule_id,
                category="unicode_tag",
                severity=severity,
                explanation=explanation,
            )
        )
    return findings


def _publish(
    findings: list[Finding],
    original: str,
    fold_mapping: list[int],
    piece_spans: Optional[list[tuple[int, int]]],
) -> list[Finding]:
    """Map findings from the decoded string back onto ``original``."""
    if piece_spans is None:
        return _remap(findings, original, fold_mapping)
    published: list[Finding] = []
    for finding in findings:
        fold_start, fold_end = map_piece_span(piece_spans, finding.start, finding.end)
        start, end = map_span(fold_mapping, fold_start, fold_end)
        span = clip_span(original[start:end])
        published.append(replace(finding, start=start, end=end, span=span))
    return published


def _spans_overlap(left: Finding, right: Finding) -> bool:
    return left.end > right.start and left.start < right.end


def _drop_shadowed_intent(findings: list[Finding]) -> list[Finding]:
    """Drop an intent hit already covered by a phrase of the same category.

    ``ignore previous instructions`` matches a phrase pack and the intent
    word list. The phrase rule is the one we show. A hidden region can make
    the intent hit look stronger; the HTML detector already reports that.
    """
    phrases = [finding for finding in findings if not finding.rule_id.startswith("intent.")]
    kept: list[Finding] = []
    for finding in findings:
        if finding.rule_id.startswith("intent."):
            shadowed = False
            for other in phrases:
                if other.category != finding.category:
                    continue
                if _spans_overlap(finding, other):
                    shadowed = True
                    break
            if shadowed:
                continue
        kept.append(finding)
    return kept


def _drop_plain_transcripts(findings: list[Finding]) -> list[Finding]:
    """Keep a role log only when some other hit sits inside it.

    Three lines such as ``System:`` / ``User:`` / ``Assistant:`` are a normal
    ops log. They count only when one of those lines is itself an instruction
    the other detectors already noticed.
    """
    others = [finding for finding in findings if finding.rule_id != "delimiter.fake_transcript"]
    kept: list[Finding] = []
    for finding in findings:
        if finding.rule_id == "delimiter.fake_transcript":
            if not any(_spans_overlap(finding, other) for other in others):
                continue
        kept.append(finding)
    return kept


def _remap(findings: list[Finding], original: str, mapping: list[int]) -> list[Finding]:
    remapped: list[Finding] = []
    for finding in findings:
        start, end = map_span(mapping, finding.start, finding.end)
        span = clip_span(original[start:end])
        remapped.append(replace(finding, start=start, end=end, span=span))
    return remapped


def _dedup(findings: list[Finding]) -> list[Finding]:
    """Drop a weaker hit that covers the same rule and overlaps a stronger one."""
    ordered = sorted(
        findings,
        key=lambda finding: (-severity_rank(finding.severity), finding.start, finding.end),
    )
    kept: list[Finding] = []
    for finding in ordered:
        overlapped = False
        for existing in kept:
            if finding.rule_id != existing.rule_id:
                continue
            if finding.end <= existing.start or finding.start >= existing.end:
                continue
            overlapped = True
            break
        if not overlapped:
            kept.append(finding)
    kept.sort(key=lambda finding: (finding.start, finding.rule_id))
    return kept


def _limit(findings: list[Finding]) -> list[Finding]:
    if len(findings) <= _MAX_FINDINGS:
        return findings
    ranked = sorted(findings, key=lambda finding: -severity_rank(finding.severity))
    trimmed = ranked[:_MAX_FINDINGS]
    trimmed.sort(key=lambda finding: (finding.start, finding.rule_id))
    return trimmed
