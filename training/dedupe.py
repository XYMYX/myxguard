"""Near-duplicate checks for the training corpus.

The held-out file must not be copied into training, and a one-word tweak of a
held-out line must not slip through either. Comparisons use a normalized form
(case, accents, punctuation, and zero-width characters removed) plus character
trigrams. This module is standard library only.
"""

from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher
from typing import Iterable, Optional, Sequence

# Drop a row when it is almost the same sentence as a blocked one.
_JACCARD_NEAR = 0.80
_RATIO_NEAR = 0.86
# Only run the slower ratio when trigrams already overlap this much.
_RATIO_FLOOR = 0.45
_CONTAIN_MIN_CHARS = 48

_ZERO_WIDTH = dict.fromkeys(
    map(ord, "\u200b\u200c\u200d\ufeff\u2060\u180e"),
    None,
)


def normalize(text: str) -> str:
    """Fold a string so trivial edits compare as the same text."""
    text = text.translate(_ZERO_WIDTH)
    text = unicodedata.normalize("NFKC", text).lower().replace("ß", "ss")
    text = "".join(
        char
        for char in unicodedata.normalize("NFKD", text)
        if not unicodedata.combining(char)
    )
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def _trigrams(text: str) -> set[str]:
    padded = f"  {text}  "
    return {padded[index : index + 3] for index in range(len(padded) - 2)}


def _jaccard(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    overlap = len(left & right)
    return overlap / (len(left) + len(right) - overlap)


class NearDupIndex:
    """Block list of texts that training must not repeat or closely paraphrase."""

    def __init__(self, texts: Iterable[str] = ()) -> None:
        self._entries: list[tuple[str, set[str]]] = []
        self.exact: set[str] = set()
        for text in texts:
            self.add(text)

    def add(self, text: str) -> None:
        folded = normalize(text)
        if not folded or folded in self.exact:
            return
        self.exact.add(folded)
        self._entries.append((folded, _trigrams(folded)))

    def reason(self, text: str) -> Optional[str]:
        """Return why ``text`` is blocked, or None if it is far enough."""
        folded = normalize(text)
        if not folded:
            return "empty"
        if folded in self.exact:
            return "exact"
        grams = _trigrams(folded)
        for other, other_grams in self._entries:
            if _contained(folded, other):
                return "contain"
            score = _jaccard(grams, other_grams)
            if score >= _JACCARD_NEAR:
                return "jaccard"
            if score < _RATIO_FLOOR:
                continue
            if min(len(folded), len(other)) > 600:
                continue
            if SequenceMatcher(None, folded, other).ratio() >= _RATIO_NEAR:
                return "ratio"
        return None

    def blocks(self, text: str) -> bool:
        return self.reason(text) is not None


def _contained(left: str, right: str) -> bool:
    shorter, longer = (left, right) if len(left) <= len(right) else (right, left)
    if len(shorter) < _CONTAIN_MIN_CHARS:
        return False
    if len(shorter) / len(longer) < 0.55:
        return False
    return shorter in longer


def disjoint_from(rows: Sequence[str], blocked: Iterable[str]) -> list[str]:
    """Return the texts in ``rows`` that are not near-duplicates of ``blocked``."""
    index = NearDupIndex(blocked)
    return [text for text in rows if not index.blocks(text)]
