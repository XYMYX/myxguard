#!/usr/bin/env python3
"""Check that CLAUDE.md carries every harness rule and lists every check tool.

Exit 0 when all rules and tools are found, 1 otherwise.

Example::

    python scripts/check_claude_md.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLAUDE_MD = ROOT / "CLAUDE.md"

# One marker per project rule in HARNESS.md. Each marker must appear verbatim.
RULE_MARKERS = {
    "categories": "instruction_override, data_exfiltration, jailbreak_persona, benign",
    "per_language": "jede Sprache einzeln",
    "roleplay_benign": "Rollenspiel-Bitten sind benign",
    "no_leakage": "training/dedupe.py",
    "false_alarms": "Fehlalarme zählen gleich viel",
    "all_numbers": "Nichts schönrechnen",
    "licenses": "THIRD_PARTY_NOTICES.md",
}


def tool_files() -> list[str]:
    """Scripts and new tests that CLAUDE.md must list."""
    names = [f"scripts/{path.name}" for path in sorted((ROOT / "scripts").glob("*.py"))]
    names += [f"tests/{path.name}" for path in sorted((ROOT / "tests").glob("test_fresh*.py"))]
    return names


def missing(text: str) -> list[str]:
    problems = [f"rule {key}: {marker!r}" for key, marker in RULE_MARKERS.items() if marker not in text]
    problems += [f"tool not listed: {name}" for name in tool_files() if name not in text]
    return problems


def main() -> int:
    if not CLAUDE_MD.is_file():
        print("CLAUDE.md missing", file=sys.stderr)
        return 1
    problems = missing(CLAUDE_MD.read_text(encoding="utf-8"))
    for problem in problems:
        print(problem)
    rules_missing = sum(problem.startswith("rule ") for problem in problems)
    tools_missing = len(problems) - rules_missing
    tools = len(tool_files())
    print(f"rules {len(RULE_MARKERS) - rules_missing}/{len(RULE_MARKERS)}, tools listed {tools - tools_missing}/{tools}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
