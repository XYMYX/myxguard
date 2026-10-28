"""Downgrade phrase hits that are clearly part of a write-up.

A security article that quotes ``ignore previous instructions`` is not the
same thing as a page that tells the model to do it. This is a heuristic: it
looks a short distance before and after the match, and it never removes the
finding. A match that sits on a code-comment line (``#``, ``//``) is lowered
the same way. Hidden HTML is not treated as a code comment, because those
bytes are really there even in a lecture.
"""

from __future__ import annotations

import re
from dataclasses import replace

from myxguard.models import Finding

# Categories produced by phrase and encoding detectors.
_PHRASE_CATEGORIES = {
    "instruction_override",
    "role_impersonation",
    "data_exfiltration",
    "tool_abuse",
    "jailbreak_persona",
    "delimiter_injection",
    "obfuscation",
}

# These words are enough on their own: the sentence is talking about an attack.
_STRONG_CUE = re.compile(
    r"(?i)\b("
    r"prompt injection|this attack|this technique|attackers use|"
    r"researchers|documentation|lecture|in this article|the phrase|known as|"
    r"dieser angriff|in diesem artikel|diese technik|"
    r"cette attaque|dans cet article|"
    r"questa tecnica|in questo articolo"
    r")\b"
)

# "For example" is common in real attacks too, so it only counts inside quotes.
_WEAK_CUE = re.compile(
    r"(?i)\b("
    r"for example|e\.g\.|such as|quote|quoted|"
    r"zum beispiel|beispielsweise|"
    r"par exemple|"
    r"ad esempio"
    r")\b"
)

_NOTE = (
    " Downgraded because the surrounding text discusses this phrase "
    "instead of issuing it."
)
_COMMENT_NOTE = " Downgraded because the match is on a code comment line."

# Cues that often come after a quotation, not before it.
_AFTER_CUE = re.compile(
    r"(?i)\b("
    r"entre guillemets|guillemets|tra virgolette|virgolette|"
    r"anf[uü]hrungszeichen|quoted|quotation|only an example|just an example|"
    r"nur ein beispiel|seulement un exemple|solo un esempio|"
    r"aux [eé]tudiants|agli studenti|f[uü]r studierende"
    r")\b"
)


def _inside_quotes(text: str, start: int) -> bool:
    """Guess whether ``start`` sits inside a quoted span.

    This is deliberately simple. It counts quote marks in a short window
    rather than trying to be a full parser.
    """
    before = text[max(0, start - 300) : start]
    if before.count('"') % 2 == 1:
        return True
    if before.count("“") > before.count("”"):
        return True
    if before.count("„") > before.count("“"):
        return True
    if before.count("«") > before.count("»"):
        return True
    return False


def looks_like_discussion(text: str, start: int, end: int) -> bool:
    """True when the match is probably an example in an article."""
    before = text[max(0, start - 120) : start]
    after = text[end : end + 120]
    if _STRONG_CUE.search(before) or _STRONG_CUE.search(after):
        return True
    if _AFTER_CUE.search(before) or _AFTER_CUE.search(after):
        return True
    if _WEAK_CUE.search(before) and _inside_quotes(text, start):
        return True
    # A colon right before a quoted payload: 'The classic string is: "..."'.
    if _inside_quotes(text, start) and before.rstrip().endswith(":"):
        return True
    return False


def on_code_comment_line(text: str, start: int) -> bool:
    """True when the match sits on a ``#``, ``//``, or SQL ``--`` line.

    HTML comments (``<!--``) are not code comments. They are a hiding place,
    so they stay at full severity.
    """
    line_start = text.rfind("\n", 0, start) + 1
    prefix = text[line_start:start].lstrip()
    if prefix.startswith("<!--") or prefix.startswith("<!"):
        return False
    if prefix.startswith("#") or prefix.startswith("//"):
        return True
    if prefix.startswith("--") and not prefix.startswith("--->"):
        return True
    return False


def apply_discussion_context(text: str, findings: list[Finding]) -> list[Finding]:
    """Lower phrase findings to ``low`` when they look like quoted examples."""
    adjusted: list[Finding] = []
    for finding in findings:
        if finding.category not in _PHRASE_CATEGORIES:
            adjusted.append(finding)
            continue
        if finding.severity == "low":
            adjusted.append(finding)
            continue
        if on_code_comment_line(text, finding.start):
            explanation = finding.explanation
            if _COMMENT_NOTE not in explanation:
                explanation = explanation.rstrip() + _COMMENT_NOTE
            adjusted.append(replace(finding, severity="low", explanation=explanation))
            continue
        if not looks_like_discussion(text, finding.start, finding.end):
            adjusted.append(finding)
            continue
        explanation = finding.explanation
        if _NOTE not in explanation:
            explanation = explanation.rstrip() + _NOTE
        adjusted.append(replace(finding, severity="low", explanation=explanation))
    return adjusted
