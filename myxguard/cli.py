"""Command-line interface: ``myxguard check`` and ``myxguard mcp``."""

from __future__ import annotations

import argparse
import os
import sys
from typing import Optional, Sequence, TextIO

from myxguard import __version__
from myxguard.mcp_server import serve
from myxguard.ml import MLModelError, MLNotInstalled
from myxguard.models import CONTENT_TYPES, ScanResult
from myxguard.scanner import scan, scan_file
from myxguard.scoring import ScanConfig

_LEVEL_COLOR = {
    "none": "\033[32m",
    "low": "\033[36m",
    "medium": "\033[33m",
    "high": "\033[31m",
    "critical": "\033[1;31m",
}
_RESET = "\033[0m"


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run the CLI and return a process exit code."""
    parser = _build_parser()
    try:
        args = parser.parse_args(list(argv) if argv is not None else None)
    except SystemExit as exc:
        code = exc.code
        if code is None:
            return 0
        return code if isinstance(code, int) else 2

    if args.command == "mcp":
        serve()
        return 0
    if args.command == "check":
        return _cmd_check(args)
    parser.print_help(sys.stderr)
    return 2


def render_human(
    result: ScanResult,
    *,
    color: bool,
    source: str,
    threshold: int,
) -> str:
    """Plain-text report used when ``--json`` is not set."""
    lines = [
        f"MyxGuard {__version__}",
        f"source: {source}",
        f"content type: {result.content_type}",
        f"risk: {_paint(result.risk_level, result.risk_level, color)} ({result.risk_score}/100)",
        f"findings: {len(result.findings)}",
        "",
    ]
    if not result.findings:
        lines.append("No prompt-injection signals found.")
    for finding in result.findings:
        language = f" [{finding.language}]" if finding.language else ""
        lines.append(
            f"[{_paint(finding.severity, finding.severity, color)}] "
            f"{finding.rule_id} ({finding.category}){language}"
        )
        lines.append(f"  at {finding.start}:{finding.end}")
        lines.append(f"  span: {finding.span}")
        lines.append(f"  {finding.explanation}")
        lines.append("")
    blocked = result.risk_score > threshold
    lines.append(f"threshold: {threshold}")
    if blocked:
        lines.append("result: score is above the threshold")
    else:
        lines.append("result: score is within the threshold")
    return "\n".join(lines).rstrip() + "\n"


def _cmd_check(args: argparse.Namespace) -> int:
    if args.threshold < 0:
        print("threshold must be 0 or greater.", file=sys.stderr)
        return 2
    languages = _parse_languages(args.languages)
    config = _scan_config(args)
    try:
        if args.file == "-":
            text = sys.stdin.read()
            result = scan(
                text,
                content_type=args.content_type,
                languages=languages,
                config=config,
            )
            source = "stdin"
        else:
            result = scan_file(
                args.file,
                content_type=args.content_type,
                languages=languages,
                config=config,
            )
            source = args.file
    except FileNotFoundError:
        print(f"File not found: {args.file}", file=sys.stderr)
        return 2
    except IsADirectoryError:
        print(f"Not a file: {args.file}", file=sys.stderr)
        return 2
    except (OSError, UnicodeError, ValueError, TypeError, MLNotInstalled, MLModelError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.json:
        print(result.to_json())
    else:
        use_color = _use_color(args.no_color, sys.stdout)
        print(
            render_human(result, color=use_color, source=source, threshold=args.threshold),
            end="",
        )
    if result.risk_score > args.threshold:
        return 1
    return 0


def _scan_config(args: argparse.Namespace) -> Optional[ScanConfig]:
    """Build a config only when the user asked for the classifier."""
    if not args.ml and not args.ml_model:
        return None
    return ScanConfig(ml=True, ml_model_path=args.ml_model)


def _parse_languages(raw: Optional[str]) -> Optional[list[str]]:
    if raw is None or raw.strip() == "":
        return None
    return [part.strip() for part in raw.split(",") if part.strip()]


def _use_color(no_color: bool, stream: TextIO) -> bool:
    if no_color or os.environ.get("NO_COLOR") is not None:
        return False
    return bool(getattr(stream, "isatty", lambda: False)())


def _paint(level: str, label: str, enabled: bool) -> str:
    if not enabled:
        return label
    color = _LEVEL_COLOR.get(level, "")
    if not color:
        return label
    return f"{color}{label}{_RESET}"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="myxguard",
        description="Scan text for prompt-injection tricks (hidden text, override phrases, obfuscation).",
    )
    parser.add_argument("--version", action="version", version=f"myxguard {__version__}")
    subparsers = parser.add_subparsers(dest="command")

    check = subparsers.add_parser("check", help="Scan a file, or stdin when the path is -")
    check.add_argument("file", help="Path to scan, or - to read stdin")
    check.add_argument("--json", action="store_true", help="Print the result as JSON")
    check.add_argument(
        "--threshold",
        type=int,
        default=0,
        help="Exit with code 1 when the score is above this value (default: 0)",
    )
    check.add_argument(
        "--content-type",
        default="auto",
        choices=list(CONTENT_TYPES),
        help="How to read the input (default: auto)",
    )
    check.add_argument(
        "--languages",
        default=None,
        help="Comma-separated language codes, for example en,de (default: all)",
    )
    check.add_argument("--no-color", action="store_true", help="Do not colour the text report")
    check.add_argument(
        "--ml",
        action="store_true",
        help="Also run the optional ONNX classifier when the rule score is below high",
    )
    check.add_argument(
        "--ml-model",
        default=None,
        help="Folder with model.onnx, tokenizer.json, and config.json (implies --ml)",
    )

    subparsers.add_parser("mcp", help="Run the MCP server on stdin/stdout")
    return parser
