"""Decode a few common disguises and scan the decoded text.

A blob is reported only when the decoded text itself matches a phrase rule.
Random Base64, hashes, and ordinary numbers stay quiet.

The set of encodings (Base64, hex, ROT13, and spaced or leetspeak letters)
follows the same idea as prompt-guard's decoder (MIT, Seojoon Kim). The
code here is written for MyxGuard: one level of decoding, no keyword list
of its own, and a match is required before anything is reported.
Percent-encoding and HTML numeric entities are included because they show
up in the same hiding tricks and need only the standard library.
"""

from __future__ import annotations

import base64
import binascii
import codecs
import re
from html import unescape
from typing import Optional, Sequence
from urllib.parse import unquote

from myxguard.detectors.delimiters import scan_transcripts
from myxguard.detectors.intent import scan_intent
from myxguard.detectors.patterns import get_rules, scan_patterns
from myxguard.models import Finding, make_finding
from myxguard.scoring import severity_rank

_MAX_CANDIDATES = 20
_MAX_DECODED = 10_000

# At least 16 alphabet characters, length a multiple of 4, optional padding.
_BASE64 = re.compile(
    r"(?<![A-Za-z0-9+/_-])"
    r"(?:[A-Za-z0-9+/]{4}){4,}(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?"
    r"(?![A-Za-z0-9+/])"
    r"|"
    r"(?<![A-Za-z0-9+/_-])"
    r"(?:[A-Za-z0-9_-]{4}){4,}(?:[A-Za-z0-9_-]{2}==|[A-Za-z0-9_-]{3}=)?"
    r"(?![A-Za-z0-9+/_-])"
)
_HEX_ESCAPES = re.compile(r"(?:\\x[0-9a-fA-F]{2}){4,}")
_HEX_RUN = re.compile(r"(?<![0-9a-fA-F])(?:[0-9a-fA-F]{2}){8,}(?![0-9a-fA-F])")
_PERCENT = re.compile(r"(?:%[0-9a-fA-F]{2}){4,}")
# Entities may be separated by spaces when each word is encoded on its own.
_HTML_ENTITIES = re.compile(
    r"(?:(?:&#x[0-9a-fA-F]+;|&#\d+;|&[a-zA-Z]+;)[ \t]*){4,}"
)
# Single letters separated by spaces, long enough to hide a word.
# One or more spaces are allowed, so both "i g n o r e" and
# "i g n o r e  p r e v i o u s" are one region.
_SPACED_REGION = re.compile(
    r"(?<![A-Za-z])((?:[A-Za-z][ \t]+){3,}[A-Za-z])(?![A-Za-z])"
)
_LEET_WORD = re.compile(r"[A-Za-z0-9@!$]{4,}")
_LEET_TABLE = str.maketrans(
    {
        "0": "o",
        "1": "i",
        "3": "e",
        "4": "a",
        "5": "s",
        "7": "t",
        "@": "a",
        "$": "s",
        "!": "i",
    }
)


def scan_obfuscation(text: str, languages: Optional[Sequence[str]] = None) -> list[Finding]:
    """Decode disguises in ``text`` and keep hits that decode to a phrase."""
    findings: list[Finding] = []
    findings.extend(_scan_blobs(text, "base64", _iter_base64(text), languages))
    findings.extend(_scan_blobs(text, "hex", _iter_hex(text), languages))
    findings.extend(_scan_blobs(text, "percent", _iter_percent(text), languages))
    findings.extend(_scan_blobs(text, "html_entity", _iter_entities(text), languages))
    findings.extend(_scan_rot13(text, languages))
    findings.extend(_scan_leetspeak(text, languages))
    findings.extend(_scan_spaced(text, languages))
    return findings


def _scan_blobs(text, kind, blobs, languages) -> list[Finding]:
    findings: list[Finding] = []
    seen: set[tuple[int, int]] = set()
    for start, end, decoded in blobs:
        if (start, end) in seen:
            continue
        seen.add((start, end))
        inner = _phrase_findings(decoded, languages)
        if not inner:
            continue
        top = max(inner, key=lambda finding: severity_rank(finding.severity))
        preview = decoded.replace("\n", " ")
        if len(preview) > 80:
            preview = preview[:77] + "..."
        findings.append(
            make_finding(
                text,
                start,
                end,
                rule_id=f"obfuscation.{kind}",
                category="obfuscation",
                severity=top.severity,
                explanation=(
                    f"{kind} decodes to text that matches {top.rule_id}: {preview!r}."
                ),
                language=top.language,
            )
        )
    return findings


def _phrase_findings(decoded: str, languages: Optional[Sequence[str]]) -> list[Finding]:
    if len(decoded) > _MAX_DECODED:
        decoded = decoded[:_MAX_DECODED]
    phrases = scan_patterns(decoded, languages)
    # A weak intent pair (verb + noun, no "previous") is not enough to call
    # a blob an attack. A plain chat log is not enough either.
    intents = [
        finding
        for finding in scan_intent(decoded, languages)
        if finding.severity != "low"
    ]
    transcripts = scan_transcripts(decoded) if intents else []
    # Keep only phrase-length hits so a tiny accidental word is not enough.
    return [
        finding
        for finding in phrases + intents + transcripts
        if len(finding.span) >= 8
    ]


def _iter_base64(text: str):
    count = 0
    for match in _BASE64.finditer(text):
        if count >= _MAX_CANDIDATES:
            return
        blob = match.group(0)
        decoded = _decode_base64(blob)
        if decoded is None:
            continue
        count += 1
        yield match.start(), match.end(), decoded


def _decode_base64(blob: str) -> Optional[str]:
    padded = blob + ("=" * ((-len(blob)) % 4))
    try:
        # urlsafe_b64decode does not accept validate=; only the standard
        # decoder does. Use it when the blob stays in the standard alphabet.
        if "-" in blob or "_" in blob:
            raw = base64.urlsafe_b64decode(padded)
        else:
            raw = base64.b64decode(padded, validate=True)
    except (binascii.Error, ValueError):
        return None
    return _as_text(raw)


def _iter_hex(text: str):
    count = 0
    for match in _HEX_ESCAPES.finditer(text):
        if count >= _MAX_CANDIDATES:
            return
        raw_hex = match.group(0).replace("\\x", "")
        decoded = _decode_hex(raw_hex)
        if decoded is None:
            continue
        count += 1
        yield match.start(), match.end(), decoded
    for match in _HEX_RUN.finditer(text):
        if count >= _MAX_CANDIDATES:
            return
        # Skip the hex we already covered as \x escapes.
        if match.group(0).startswith("\\"):
            continue
        decoded = _decode_hex(match.group(0))
        if decoded is None or " " not in decoded:
            # A hash rarely decodes to words separated by spaces. Require one.
            continue
        count += 1
        yield match.start(), match.end(), decoded


def _decode_hex(raw_hex: str) -> Optional[str]:
    try:
        raw = bytes.fromhex(raw_hex)
    except ValueError:
        return None
    return _as_text(raw)


def _iter_percent(text: str):
    count = 0
    for match in _PERCENT.finditer(text):
        if count >= _MAX_CANDIDATES:
            return
        decoded = unquote(match.group(0))
        if not _as_text(decoded.encode("utf-8", errors="ignore")):
            continue
        if decoded == match.group(0):
            continue
        count += 1
        yield match.start(), match.end(), decoded


def _iter_entities(text: str):
    count = 0
    for match in _HTML_ENTITIES.finditer(text):
        if count >= _MAX_CANDIDATES:
            return
        decoded = unescape(match.group(0))
        if decoded == match.group(0) or _as_text(decoded.encode("utf-8", errors="ignore")) is None:
            continue
        count += 1
        yield match.start(), match.end(), decoded


def _scan_rot13(text: str, languages: Optional[Sequence[str]]) -> list[Finding]:
    letters = sum(1 for char in text if char.isalpha())
    if letters < 12 or letters / max(len(text), 1) < 0.5:
        return []
    decoded = codecs.decode(text, "rot_13")
    if decoded == text:
        return []
    inner = _phrase_findings(decoded, languages)
    if not inner:
        return []
    # Highlight the decoded phrase's location. ROT13 keeps indexes aligned.
    findings: list[Finding] = []
    for finding in inner[:5]:
        original_slice = text[finding.start : finding.end]
        if original_slice.lower() == finding.span.lower():
            continue
        findings.append(
            make_finding(
                text,
                finding.start,
                finding.end,
                rule_id="obfuscation.rot13",
                category="obfuscation",
                severity=finding.severity,
                explanation=(
                    f"ROT13 decodes this span to text that matches {finding.rule_id}: "
                    f"{finding.span!r}."
                ),
                language=finding.language,
            )
        )
    return findings


def _scan_leetspeak(text: str, languages: Optional[Sequence[str]]) -> list[Finding]:
    if not any(char.isdigit() or char in "@!$" for char in text):
        return []

    def replace(match: re.Match[str]) -> str:
        word = match.group(0)
        if not any(char.isdigit() or char in "@!$" for char in word):
            return word
        if not any(char.isalpha() for char in word):
            return word
        return word.translate(_LEET_TABLE)

    translated = _LEET_WORD.sub(replace, text)
    if translated == text:
        return []
    inner = _phrase_findings(translated, languages)
    findings: list[Finding] = []
    for finding in inner[:5]:
        # Translation is one character to one character, so indexes still match.
        original_slice = text[finding.start : finding.end]
        if original_slice == translated[finding.start : finding.end]:
            continue
        findings.append(
            make_finding(
                text,
                finding.start,
                finding.end,
                rule_id="obfuscation.leetspeak",
                category="obfuscation",
                severity=finding.severity,
                explanation=(
                    "Leetspeak in this span reads as "
                    f"{translated[finding.start:finding.end]!r}, "
                    f"which matches {finding.rule_id}."
                ),
                language=finding.language,
            )
        )
    return findings


def _scan_spaced(text: str, languages: Optional[Sequence[str]]) -> list[Finding]:
    """Join ``i g n o r e`` back into words, then match phrases.

    Spaces inside the joined text are optional in the rule (``ignoreprevious``
    still counts). A hit is kept only when some of those spaces were really
    removed, so a normal sentence is not reported twice.
    """
    collapsed, index_map = _collapse_spaced(text)
    if collapsed is None or index_map is None:
        return []
    findings: list[Finding] = []
    for rule in get_rules(languages):
        try:
            relaxed = re.compile(rule.regex.pattern.replace(r"\s+", r"\s*"))
        except re.error:
            continue
        matches = 0
        for match in relaxed.finditer(collapsed):
            matches += 1
            if matches > 5:
                break
            if match.end() - match.start() < 8 or match.start() >= len(index_map):
                continue
            last = min(match.end() - 1, len(index_map) - 1)
            source_start = index_map[match.start()]
            source_end = index_map[last] + 1
            plain = collapsed[match.start() : match.end()]
            if source_end - source_start <= len(plain):
                continue
            findings.append(
                make_finding(
                    text,
                    source_start,
                    source_end,
                    rule_id="obfuscation.spaced_letters",
                    category="obfuscation",
                    severity=rule.severity,
                    explanation=(
                        f"Spaced-out letters collapse to {plain!r}, "
                        f"which matches {rule.rule_id}."
                    ),
                    language=rule.language,
                )
            )
    return findings


def _collapse_spaced(text: str) -> tuple[Optional[str], Optional[list[int]]]:
    pieces: list[str] = []
    index_map: list[int] = []
    last = 0
    changed = False
    for match in _SPACED_REGION.finditer(text):
        for index in range(last, match.start()):
            pieces.append(text[index])
            index_map.append(index)
        # group 1 starts at the same index as the whole match.
        for offset, char in enumerate(match.group(1)):
            if char.isalpha():
                pieces.append(char)
                index_map.append(match.start() + offset)
        changed = True
        last = match.end()
    if not changed:
        return None, None
    for index in range(last, len(text)):
        pieces.append(text[index])
        index_map.append(index)
    return "".join(pieces), index_map


def _as_text(raw: bytes) -> Optional[str]:
    """Accept decoded bytes only when they look like a short piece of text."""
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return None
    if len(text) < 8:
        return None
    printable = sum(1 for char in text if char.isprintable() or char in "\n\t")
    if printable / len(text) < 0.9:
        return None
    if not any(char.isalpha() for char in text):
        return None
    return text
