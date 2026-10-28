"""The README examples are the live CLI and benchmark output."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run(args):
    return subprocess.run(
        [sys.executable, *args],
        text=True,
        capture_output=True,
        check=False,
        cwd=ROOT,
    )


def test_readmes_quote_live_cli_and_benchmark_output():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    readme_de = (ROOT / "README.de.md").read_text(encoding="utf-8")
    commands = [
        ["-m", "myxguard", "check", "examples/ignore.txt", "--no-color"],
        ["-m", "myxguard", "check", "examples/ignore.txt", "--json", "--no-color"],
        ["-m", "myxguard", "check", "examples/hidden.html", "--no-color"],
        ["-m", "myxguard", "check", "examples/benign.txt", "--no-color"],
        ["-m", "myxguard", "check", "examples/swiss.txt", "--no-color"],
        ["scripts/benchmark.py", "datasets/samples.jsonl"],
        ["scripts/benchmark.py", "datasets/deepset_sample.jsonl"],
    ]
    for args in commands:
        completed = _run(args)
        assert completed.returncode in (0, 1), completed.stderr
        assert completed.stdout, args
        assert completed.stdout in readme, args
        assert completed.stdout in readme_de, args
