"""Small string helpers shared by the detectors.

Attackers drop invisible characters inside a word (``ign<zwsp>ore``) so a
plain keyword search misses it. :func:`fold_text` removes those characters
for the keyword pass and remembers where each remaining character came from,
so a match can still be highlighted in the original text.
"""

from __future__ import annotations

import re

# Characters we delete only for matching. The Unicode detector still sees
# them in the original string and can report them on its own.
_STRIP_EXTRA = {
    "\u00ad",  # soft hyphen
    "\u034f",  # combining grapheme joiner
    "\u061c",  # Arabic letter mark
    "\u115f",  # Hangul choseong filler
    "\u1160",  # Hangul jungseong filler
    "\u17b4",  # Khmer vowel inherent AQ
    "\u17b5",  # Khmer vowel inherent AA
    "\u180e",  # Mongolian vowel separator
    "\u200b",  # zero-width space
    "\u200c",  # zero-width non-joiner
    "\u200d",  # zero-width joiner
    "\u200e",  # left-to-right mark
    "\u200f",  # right-to-left mark
    "\u202a",  # left-to-right embedding
    "\u202b",  # right-to-left embedding
    "\u202c",  # pop directional formatting
    "\u202d",  # left-to-right override
    "\u202e",  # right-to-left override
    "\u2060",  # word joiner
    "\u2061",  # function application
    "\u2062",  # invisible times
    "\u2063",  # invisible separator
    "\u2064",  # invisible plus
    "\u2066",  # left-to-right isolate
    "\u2067",  # right-to-left isolate
    "\u2068",  # first strong isolate
    "\u2069",  # pop directional isolate
    "\u3164",  # Hangul filler
    "\ufeff",  # zero-width no-break space / BOM
    "\uffa0",  # halfwidth Hangul filler
}


def is_fold_char(char: str) -> bool:
    """True when ``char`` should be ignored while looking for phrases."""
    if char in _STRIP_EXTRA:
        return True
    code = ord(char)
    # Variation selectors (BMP and the supplement plane).
    if 0xFE00 <= code <= 0xFE0F or 0xE0100 <= code <= 0xE01EF:
        return True
    # Unicode Tags (U+E0000 block), including the ASCII-smuggling range.
    if code == 0xE0001 or 0xE0020 <= code <= 0xE007F:
        return True
    return False


def fold_text(text: str) -> tuple[str, list[int]]:
    """Return text without fold-characters, plus a map back to ``text``.

    ``mapping[i]`` is the index in ``text`` of folded character ``i``.
    """
    chars: list[str] = []
    mapping: list[int] = []
    for index, char in enumerate(text):
        if is_fold_char(char):
            continue
        chars.append(char)
        mapping.append(index)
    return "".join(chars), mapping


def map_span(mapping: list[int], start: int, end: int) -> tuple[int, int]:
    """Convert a span in folded text back to a span in the original text."""
    if end <= start or not mapping:
        return 0, 0
    if start < 0:
        start = 0
    if start >= len(mapping):
        return mapping[-1] + 1, mapping[-1] + 1
    last = end - 1
    if last >= len(mapping):
        last = len(mapping) - 1
    if last < start:
        last = start
    return mapping[start], mapping[last] + 1


# ``\xHH``, ``\uHHHH`` and ``\UHHHHHHHH`` written as text, not as real characters.
_INLINE_ESCAPE = re.compile(
    r"\\x([0-9a-fA-F]{2})|\\u([0-9a-fA-F]{4})|\\U([0-9a-fA-F]{8})"
)


def decode_inline_escapes(
    text: str,
) -> tuple[str, list[tuple[int, int]] | None]:
    """Turn ``\\x20``-style escapes into characters.

    Returns the decoded string and, for each decoded character, the
    ``(start, end)`` offsets of the piece that produced it. ``None`` for the
    map means the text had no escapes, so the caller can skip a second pass.
    """
    if _INLINE_ESCAPE.search(text) is None:
        return text, None
    chars: list[str] = []
    spans: list[tuple[int, int]] = []
    last = 0
    for match in _INLINE_ESCAPE.finditer(text):
        for index in range(last, match.start()):
            chars.append(text[index])
            spans.append((index, index + 1))
        digits = match.group(1) or match.group(2) or match.group(3)
        code = int(digits, 16)
        if code > 0x10FFFF or 0xD800 <= code <= 0xDFFF:
            for index in range(match.start(), match.end()):
                chars.append(text[index])
                spans.append((index, index + 1))
        else:
            chars.append(chr(code))
            spans.append((match.start(), match.end()))
        last = match.end()
    for index in range(last, len(text)):
        chars.append(text[index])
        spans.append((index, index + 1))
    return "".join(chars), spans


def map_piece_span(
    spans: list[tuple[int, int]],
    start: int,
    end: int,
) -> tuple[int, int]:
    """Map a span in decoded text back onto the string that was decoded."""
    if end <= start or not spans:
        return 0, 0
    if start < 0:
        start = 0
    if start >= len(spans):
        return spans[-1][1], spans[-1][1]
    last = end - 1
    if last >= len(spans):
        last = len(spans) - 1
    if last < start:
        last = start
    return spans[start][0], spans[last][1]
