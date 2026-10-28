"""Hidden and misleading Unicode.

What this looks for:

* zero-width and other invisible characters
* bidi overrides (for example right-to-left override, U+202E)
* Unicode Tag characters, which can hide an ASCII string
* variation selectors sitting on ordinary letters
* a word that mixes Latin letters with Cyrillic or Greek lookalikes

Emoji sequences use a zero-width joiner on purpose (family emoji, and so on).
Those joiners are left alone. A single byte-order mark at the start of a
file is also normal and is ignored.

The idea of "invisible Unicode is suspicious" is discussed in llm-guard's
invisible-text scanner (MIT, Protect AI). This file does not copy that
scanner. llm-guard flags every character in the Unicode categories Cf, Co,
and Cn, which also flags normal Arabic and Hebrew formatting. MyxGuard names
the characters it cares about instead. See THIRD_PARTY_NOTICES.md.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from myxguard.models import Finding, make_finding

# Zero-width and other characters that should not show up inside a prompt.
_ZERO_WIDTH = frozenset(
    {
        "\u00ad",
        "\u034f",
        "\u115f",
        "\u1160",
        "\u17b4",
        "\u17b5",
        "\u180e",
        "\u200b",
        "\u200c",
        "\u200d",
        "\u2060",
        "\u2061",
        "\u2062",
        "\u2063",
        "\u2064",
        "\u3164",
        "\ufeff",
        "\uffa0",
    }
)

# Direction overrides change the order of the characters that follow them.
# U+202C (PDF) only closes an override, so it is not a signal by itself.
_BIDI_OVERRIDE = frozenset("\u202a\u202b\u202d\u202e")
_BIDI_ISOLATE = frozenset("\u2066\u2067\u2068\u2069")
_DIRECTION_MARK = frozenset("\u200e\u200f\u061c")

# A run of single letters. Used only to decide word boundaries for homoglyphs.
_WORD = re.compile(r"[^\W\d_]{3,}", re.UNICODE)


@dataclass(frozen=True)
class TagPayload:
    """ASCII recovered from a run of Unicode Tag characters."""

    start: int
    end: int
    decoded: str


@dataclass(frozen=True)
class UnicodeScan:
    findings: list[Finding]
    tag_payloads: list[TagPayload]


def scan_unicode(text: str) -> UnicodeScan:
    """Scan ``text`` for invisible and mixed-script tricks."""
    findings: list[Finding] = []
    findings.extend(_zero_width_findings(text))
    findings.extend(_bidi_findings(text))
    findings.extend(_variation_selector_findings(text))
    findings.extend(_homoglyph_findings(text))
    payloads, tag_findings = _tag_findings(text)
    findings.extend(tag_findings)
    return UnicodeScan(findings=findings, tag_payloads=payloads)


def _zero_width_findings(text: str) -> list[Finding]:
    findings: list[Finding] = []
    for start, end in _runs(text, _is_reportable_zero_width):
        count = end - start
        severity = "medium" if count >= 3 else "low"
        names = sorted({_code_name(text[index]) for index in range(start, end)})
        findings.append(
            make_finding(
                text,
                start,
                end,
                rule_id="unicode.zero_width",
                category="invisible_unicode",
                severity=severity,
                explanation=(
                    f"Found {count} invisible character(s) ({', '.join(names)}). "
                    "They can split a word so a person does not see the break."
                ),
            )
        )
    return findings


def _is_reportable_zero_width(text: str, index: int) -> bool:
    char = text[index]
    if char not in _ZERO_WIDTH:
        return False
    # A BOM at the very start is how some editors save UTF-8.
    if char == "\ufeff" and index == 0:
        return False
    # ZWJ between two emoji is how "family" and similar emoji are built.
    if char == "\u200d" and _zwj_joins_emoji(text, index):
        return False
    return True


def _zwj_joins_emoji(text: str, index: int) -> bool:
    if index == 0 or index + 1 >= len(text):
        return False
    return _is_emoji(text[index - 1]) and _is_emoji(text[index + 1])


def _is_emoji(char: str) -> bool:
    code = ord(char)
    if code >= 0x1F000 or 0x2600 <= code <= 0x27BF or 0x2300 <= code <= 0x23FF:
        return True
    return unicodedata.category(char) in {"So", "Sk"}


def _bidi_findings(text: str) -> list[Finding]:
    findings: list[Finding] = []
    for start, end in _runs(text, lambda value, index: value[index] in _BIDI_OVERRIDE):
        findings.append(
            make_finding(
                text,
                start,
                end,
                rule_id="unicode.bidi_override",
                category="bidi_control",
                severity="high",
                explanation=(
                    "Bidirectional override characters change the display order "
                    "of the letters around them. A reader can see a different "
                    "word from the one the model receives."
                ),
            )
        )
    isolate_count = sum(1 for char in text if char in _BIDI_ISOLATE)
    if isolate_count:
        start = next(index for index, char in enumerate(text) if char in _BIDI_ISOLATE)
        end = start + 1
        severity = "medium" if isolate_count >= 3 else "low"
        findings.append(
            make_finding(
                text,
                start,
                end,
                rule_id="unicode.bidi_isolate",
                category="bidi_control",
                severity=severity,
                explanation=(
                    f"Found {isolate_count} bidi isolate character(s). "
                    "A few can be legitimate in mixed-language text; "
                    "several of them are unusual in a plain prompt."
                ),
            )
        )
    mark_count = sum(1 for char in text if char in _DIRECTION_MARK)
    if mark_count >= 4:
        start = next(index for index, char in enumerate(text) if char in _DIRECTION_MARK)
        findings.append(
            make_finding(
                text,
                start,
                start + 1,
                rule_id="unicode.direction_marks",
                category="bidi_control",
                severity="low",
                explanation=(
                    f"Found {mark_count} left-to-right or right-to-left marks. "
                    "A handful are normal in bidirectional text; this many is worth a look."
                ),
            )
        )
    return findings


def _variation_selector_findings(text: str) -> list[Finding]:
    findings: list[Finding] = []
    for start, end in _runs(text, lambda value, index: _is_abusive_variation(value, index)):
        findings.append(
            make_finding(
                text,
                start,
                end,
                rule_id="unicode.variation_selector",
                category="variation_selector",
                severity="medium",
                explanation=(
                    "Variation selectors are attached to ordinary letters. "
                    "On an emoji they choose a style; on a letter they usually "
                    "hide extra code points inside a word."
                ),
            )
        )
    return findings


def _is_variation(char: str) -> bool:
    code = ord(char)
    return 0xFE00 <= code <= 0xFE0F or 0xE0100 <= code <= 0xE01EF


def _is_abusive_variation(text: str, index: int) -> bool:
    if not _is_variation(text[index]):
        return False
    if index == 0:
        return True
    previous = text[index - 1]
    if _is_variation(previous):
        return True
    # A selector after an ASCII letter or digit is not an emoji presentation.
    return previous.isascii() and previous.isalnum()


def _homoglyph_findings(text: str) -> list[Finding]:
    findings: list[Finding] = []
    for match in _WORD.finditer(text):
        word = match.group(0)
        scripts = {_script_of(char) for char in word}
        scripts.discard("other")
        mixed = "latin" in scripts and ("cyrillic" in scripts or "greek" in scripts)
        if not mixed:
            continue
        shown = ", ".join(sorted(scripts))
        findings.append(
            make_finding(
                text,
                match.start(),
                match.end(),
                rule_id="unicode.homoglyph",
                category="homoglyph",
                severity="medium",
                explanation=(
                    f"The word {word!r} mixes scripts ({shown}). "
                    "A Cyrillic or Greek letter can look like a Latin one, "
                    "so the word is not the word it appears to be."
                ),
            )
        )
    return findings


def _script_of(char: str) -> str:
    code = ord(char)
    if 0x0400 <= code <= 0x052F or 0x2DE0 <= code <= 0x2DFF or 0xA640 <= code <= 0xA69F:
        return "cyrillic"
    if 0x0370 <= code <= 0x03FF or 0x1F00 <= code <= 0x1FFF:
        return "greek"
    if ("A" <= char <= "Z") or ("a" <= char <= "z") or 0x00C0 <= code <= 0x024F:
        return "latin"
    # Rare letters outside the blocks above. The name lookup is the fallback.
    name = unicodedata.name(char, "")
    if "CYRILLIC" in name:
        return "cyrillic"
    if "GREEK" in name:
        return "greek"
    if "LATIN" in name:
        return "latin"
    return "other"


def _tag_findings(text: str) -> tuple[list[TagPayload], list[Finding]]:
    payloads: list[TagPayload] = []
    findings: list[Finding] = []
    for start, end in _runs(text, lambda value, index: _is_tag_char(value[index])):
        decoded = _decode_tags(text[start:end])
        letters = sum(1 for char in decoded if char.isalnum())
        if letters >= 4:
            payloads.append(TagPayload(start=start, end=end, decoded=decoded))
            continue
        findings.append(
            make_finding(
                text,
                start,
                end,
                rule_id="unicode.tag.fragment",
                category="unicode_tag",
                severity="medium",
                explanation=(
                    "Unicode Tag characters are present but they do not decode "
                    "to a readable ASCII string. They are invisible in most fonts."
                ),
            )
        )
    return payloads, findings


def _is_tag_char(char: str) -> bool:
    code = ord(char)
    return code == 0xE0001 or 0xE0020 <= code <= 0xE007F


def _decode_tags(chunk: str) -> str:
    """Turn tag characters back into ASCII. Other tag chars are dropped."""
    chars: list[str] = []
    for char in chunk:
        code = ord(char)
        if 0xE0020 <= code <= 0xE007E:
            chars.append(chr(code - 0xE0000))
    return "".join(chars)


def _runs(text: str, predicate) -> list[tuple[int, int]]:
    """Yield [start, end) runs where ``predicate(text, index)`` is true."""
    ranges: list[tuple[int, int]] = []
    start: int | None = None
    for index in range(len(text)):
        if predicate(text, index):
            if start is None:
                start = index
        elif start is not None:
            ranges.append((start, index))
            start = None
    if start is not None:
        ranges.append((start, len(text)))
    return ranges


def _code_name(char: str) -> str:
    return f"U+{ord(char):04X}"
