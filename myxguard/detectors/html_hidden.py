"""Hidden text inside HTML, parsed with the standard-library HTML parser.

Inline style is checked for the usual hiding tricks: ``display:none``,
``visibility:hidden``, a font size of about zero, opacity at or near zero,
the same text and background colour, and a large negative position.
Boolean ``hidden``, ``aria-hidden="true"``, HTML comments, and ``alt`` /
``title`` text are checked too.

A cookie banner that is merely ``display:none`` is reported as low, because
real pages do that. The same markup is high when the hidden text itself
matches an instruction rule. Stylesheet classes (``.hidden { display:none }``)
are not followed; that limitation is documented in the README.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from typing import Optional, Sequence

from myxguard.detectors.patterns import scan_patterns
from myxguard.models import Finding, make_finding
from myxguard.textutil import is_fold_char

_VOID_TAGS = {
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "source",
    "track",
    "wbr",
}

_SKIP_TEXT_TAGS = {"script", "style", "noscript"}

_NAMED_COLORS = {
    "white": "ffffff",
    "black": "000000",
    "red": "ff0000",
    "blue": "0000ff",
    "green": "008000",
    "yellow": "ffff00",
    "silver": "c0c0c0",
    "gray": "808080",
    "grey": "808080",
}

_BOILERPLATE_COMMENT = re.compile(
    r"(?i)\b(copyright|all rights reserved|urheberrecht|lizenz|license|"
    r"endif|\[if|generator|todo|fixme|google tag manager)\b"
)

_WORD = re.compile(r"[A-Za-zÀ-ÿ]{2,}")


def scan_html(text: str, languages: Optional[Sequence[str]] = None) -> list[Finding]:
    """Return concealment findings and phrase hits rebuilt from text nodes."""
    parser = _HiddenHTMLParser(text, languages)
    parser.feed(text)
    parser.close()
    parser.flush_open_frames()
    return parser.findings


class _HiddenHTMLParser(HTMLParser):
    """Collect hidden regions while remembering source offsets."""

    def __init__(self, text: str, languages: Optional[Sequence[str]]) -> None:
        # Keep entities as they appear so ``len(data)`` matches the source.
        super().__init__(convert_charrefs=False)
        self.text = text
        self.languages = languages
        self.line_starts = _line_starts(text)
        self.stack: list[dict] = []
        self.findings: list[Finding] = []
        self._plain_chars: list[str] = []
        self._plain_origin: list[int] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        self._start(tag, attrs, void=tag.lower() in _VOID_TAGS)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        self._start(tag, attrs, void=True)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index]["tag"] != tag:
                continue
            for frame in self.stack[index:]:
                self._close_frame(frame)
            del self.stack[index:]
            return

    def handle_data(self, data: str) -> None:
        abs_start = self._absolute()
        if self._skip_depth == 0:
            self._add_plain(abs_start, data)
        receiver = self._receiver()
        if receiver is None or not data:
            return
        if receiver["start"] is None:
            receiver["start"] = abs_start
        receiver["parts"].append(data)
        receiver["end"] = abs_start + len(data)

    def handle_comment(self, data: str) -> None:
        # getpos() points at the '<' of '<!--'. The comment body starts 4 later.
        body_start = self._absolute() + 4
        body_end = body_start + len(data)
        if body_end > len(self.text):
            body_end = len(self.text)
        hostile = _snippet_is_hostile(data, self.languages)
        if hostile:
            severity = "high"
        elif _BOILERPLATE_COMMENT.search(data) or len(_WORD.findall(data)) < 8:
            return
        else:
            severity = "low"
        explanation = "An HTML comment hides text from a reader but not from a parser."
        if hostile:
            explanation += " The comment matches an instruction pattern."
        self.findings.append(
            make_finding(
                self.text,
                max(0, body_start),
                body_end,
                rule_id="html.comment",
                category="hidden_html",
                severity=severity,
                explanation=explanation,
            )
        )

    def flush_open_frames(self) -> None:
        """Report hidden tags that never closed, then scan rebuilt text."""
        while self.stack:
            self._close_frame(self.stack.pop())
        self._scan_rebuilt_text()

    def _start(self, tag: str, attrs: list[tuple[str, Optional[str]]], *, void: bool) -> None:
        tag = tag.lower()
        attr_map = {(name or "").lower(): value for name, value in attrs}
        reason = _hidden_reason(tag, attr_map)
        tag_pos = self._absolute()
        self._scan_alt_title(tag_pos, attr_map)
        if tag in _SKIP_TEXT_TAGS:
            self._skip_depth += 1
        if void:
            return
        self.stack.append(
            {
                "tag": tag,
                "reason": reason,
                "parts": [],
                "start": None,
                "end": None,
                "skipped": tag in _SKIP_TEXT_TAGS,
            }
        )

    def _close_frame(self, frame: dict) -> None:
        if frame.get("skipped"):
            self._skip_depth = max(0, self._skip_depth - 1)
        if not frame["reason"]:
            return
        snippet = "".join(frame["parts"])
        if not snippet.strip():
            return
        start = frame["start"] if frame["start"] is not None else 0
        end = frame["end"] if frame["end"] is not None else start
        hostile = _snippet_is_hostile(snippet, self.languages)
        severity = _concealment_severity(frame["reason"], hostile)
        readable = " ".join(snippet.split())
        if len(readable) > 120:
            readable = readable[:117] + "..."
        explanation = (
            f"HTML hides this text with {frame['reason'].replace('_', ' ')}: {readable!r}."
        )
        if hostile:
            explanation += " The hidden text matches an instruction pattern."
        self.findings.append(
            make_finding(
                self.text,
                start,
                end,
                rule_id=f"html.{frame['reason']}",
                category="hidden_html",
                severity=severity,
                explanation=explanation,
            )
        )

    def _receiver(self) -> Optional[dict]:
        for frame in reversed(self.stack):
            if frame["reason"] and not frame.get("skipped"):
                return frame
        return None

    def _add_plain(self, source_start: int, data: str) -> None:
        for offset, char in enumerate(data):
            if is_fold_char(char):
                continue
            self._plain_chars.append(char)
            self._plain_origin.append(source_start + offset)

    def _scan_rebuilt_text(self) -> None:
        """Match phrases after tags that were sitting between the words."""
        if not self._plain_chars:
            return
        plain = "".join(self._plain_chars)
        for finding in scan_patterns(plain, self.languages):
            if finding.end <= finding.start:
                continue
            if finding.start >= len(self._plain_origin):
                continue
            last = min(finding.end - 1, len(self._plain_origin) - 1)
            source_start = self._plain_origin[finding.start]
            source_end = self._plain_origin[last] + 1
            plain_match = plain[finding.start : finding.end]
            explanation = finding.explanation
            source_slice = self.text[source_start:source_end]
            if source_slice != plain_match:
                explanation += f" Text with markup removed: {plain_match}."
            self.findings.append(
                make_finding(
                    self.text,
                    source_start,
                    source_end,
                    rule_id=finding.rule_id,
                    category=finding.category,
                    severity=finding.severity,
                    explanation=explanation,
                    language=finding.language,
                )
            )

    def _scan_alt_title(self, tag_pos: int, attr_map: dict[str, Optional[str]]) -> None:
        for name in ("alt", "title"):
            value = attr_map.get(name)
            if not value or not str(value).strip():
                continue
            if not _snippet_is_hostile(str(value), self.languages):
                continue
            span = _find_attr_span(self.text, tag_pos, name, str(value))
            if span is None:
                continue
            start, end = span
            self.findings.append(
                make_finding(
                    self.text,
                    start,
                    end,
                    rule_id=f"html.{name}_instruction",
                    category="hidden_html",
                    severity="high",
                    explanation=(
                        f"The {name} attribute is not shown as body text, "
                        "and it matches an instruction pattern."
                    ),
                )
            )

    def _absolute(self) -> int:
        line, offset = self.getpos()
        if line < 1 or line > len(self.line_starts):
            return 0
        return self.line_starts[line - 1] + offset


def _hidden_reason(tag: str, attrs: dict[str, Optional[str]]) -> Optional[str]:
    if "hidden" in attrs:
        return "hidden_attribute"
    aria = (attrs.get("aria-hidden") or "").strip().lower()
    if aria == "true":
        return "aria_hidden"
    if tag == "font" and (attrs.get("size") or "").strip() == "0":
        return "font_size"
    style = _parse_style(attrs.get("style") or "")
    if not style and tag == "font":
        # <font color="white"> alone is not enough; the page background is unknown.
        return None
    if _css_is(style.get("display"), "none"):
        return "display_none"
    if _css_is(style.get("visibility"), "hidden") or _css_is(style.get("visibility"), "collapse"):
        return "visibility_hidden"
    if _font_size_hidden(style.get("font-size")):
        return "font_size"
    if _opacity_hidden(style.get("opacity")):
        return "opacity_zero"
    if _offscreen(style):
        return "offscreen"
    if _same_color(style, attrs):
        return "same_color"
    return None


def _concealment_severity(reason: str, hostile: bool) -> str:
    if hostile:
        return "high"
    # These are less common in ordinary pages than display:none.
    if reason in {"same_color", "font_size", "offscreen"}:
        return "medium"
    return "low"


def _snippet_is_hostile(snippet: str, languages: Optional[Sequence[str]]) -> bool:
    folded = "".join(char for char in snippet if not is_fold_char(char))
    return bool(scan_patterns(folded, languages))


def _parse_style(style: str) -> dict[str, str]:
    props: dict[str, str] = {}
    for part in style.split(";"):
        if ":" not in part:
            continue
        key, value = part.split(":", 1)
        props[key.strip().lower()] = value.strip().lower()
    return props


def _css_is(value: Optional[str], expected: str) -> bool:
    if not value:
        return False
    token = value.split("!", 1)[0].strip().lower()
    return token == expected


def _font_size_hidden(value: Optional[str]) -> bool:
    if not value:
        return False
    match = re.match(r"([0-9]*\.?[0-9]+)\s*(px|pt|em|rem|%)?", value.strip())
    if not match:
        return False
    number = float(match.group(1))
    unit = match.group(2) or "px"
    if unit in {"px", "pt"} and number <= 1:
        return True
    if unit in {"em", "rem", "%"} and number == 0:
        return True
    return False


def _opacity_hidden(value: Optional[str]) -> bool:
    if not value:
        return False
    token = value.split("!", 1)[0].strip()
    match = re.match(r"([0-9]*\.?[0-9]+)\s*%?", token)
    if not match:
        return False
    number = float(match.group(1))
    if token.endswith("%"):
        return number <= 5
    # 0.05 is a common "basically invisible" value. 0.5 is a normal fade.
    return number <= 0.05


def _offscreen(style: dict[str, str]) -> bool:
    if _largely_negative(style.get("text-indent")):
        return True
    position = (style.get("position") or "").split("!", 1)[0].strip()
    if position not in {"absolute", "fixed"}:
        return False
    return any(_largely_negative(style.get(prop)) for prop in ("left", "top", "right"))


def _largely_negative(value: Optional[str]) -> bool:
    if not value:
        return False
    match = re.match(r"(-?[0-9]*\.?[0-9]+)", value.strip())
    if not match:
        return False
    return float(match.group(1)) <= -500


def _same_color(style: dict[str, str], attrs: dict[str, Optional[str]]) -> bool:
    foreground = _normalize_color(style.get("color") or attrs.get("color") or "")
    background = _normalize_color(
        style.get("background-color") or _first_color(style.get("background") or "")
    )
    if not foreground or not background:
        return False
    return foreground == background


def _first_color(value: str) -> str:
    """Pull a colour out of a ``background`` shorthand if one is present."""
    for token in value.replace("(", " (").split():
        if token.startswith("#") or token in _NAMED_COLORS or token.startswith("rgb"):
            # Put the rest of an rgb() triple back together when we split it.
            if token.startswith("rgb"):
                return value
            return token
    return ""


def _normalize_color(value: str) -> Optional[str]:
    if not value:
        return None
    value = value.strip().lower()
    if value in _NAMED_COLORS:
        return _NAMED_COLORS[value]
    hex_match = re.fullmatch(r"#([0-9a-f]{3}|[0-9a-f]{6})", value)
    if hex_match:
        hex_digits = hex_match.group(1)
        if len(hex_digits) == 3:
            hex_digits = "".join(char * 2 for char in hex_digits)
        return hex_digits
    rgb_match = re.fullmatch(
        r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)",
        value,
    )
    if not rgb_match:
        return None
    channels = [max(0, min(255, int(rgb_match.group(index)))) for index in (1, 2, 3)]
    return "".join(f"{channel:02x}" for channel in channels)


def _find_attr_span(text: str, tag_pos: int, name: str, value: str) -> Optional[tuple[int, int]]:
    window_end = min(len(text), tag_pos + 800)
    window = text[tag_pos:window_end]
    pattern = re.compile(
        rf"{re.escape(name)}\s*=\s*(['\"]){re.escape(value)}\1",
        re.IGNORECASE,
    )
    match = pattern.search(window)
    if not match:
        return None
    return tag_pos + match.start(0), tag_pos + match.end(0)


def _line_starts(text: str) -> list[int]:
    starts = [0]
    for index, char in enumerate(text):
        if char == "\n":
            starts.append(index + 1)
    return starts
