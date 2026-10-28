"""Fake chat transcripts.

Single tokens such as ``<|im_start|>`` live in ``data/patterns/common.json``
so they can be extended like any other phrase. This module only catches a
different shape: several ``Role:`` lines that look like a pasted conversation.

One line such as ``System: the heating is on`` is normal in logs, so it is
not enough on its own. A plain three-line log is also normal. ``scan`` drops
that hit unless another detector finds an instruction inside the same span.
Vigil (Apache-2.0) and prompt-guard (MIT) list the special tokens; the
transcript counter is original. See THIRD_PARTY_NOTICES.md.
"""

from __future__ import annotations

import re

from myxguard.models import Finding, make_finding

# A role label at the start of a line, followed by some text.
_ROLE_LINE = re.compile(
    r"(?im)^\s*(system|assistant|user|human|developer)\s*:\s+\S"
)


def scan_transcripts(text: str) -> list[Finding]:
    """Flag a block that imitates a multi-turn chat log."""
    matches = list(_ROLE_LINE.finditer(text))
    roles = {match.group(1).lower() for match in matches}
    if len(matches) < 3 or len(roles) < 2:
        return []
    start = matches[0].start()
    end = matches[-1].end()
    role_list = ", ".join(sorted(roles))
    return [
        make_finding(
            text,
            start,
            end,
            rule_id="delimiter.fake_transcript",
            category="delimiter_injection",
            severity="medium",
            explanation=(
                "Several chat role lines "
                f"({role_list}) appear together. Pasted transcripts are a "
                "common way to smuggle a fake system turn."
            ),
            language="multi",
        )
    ]
