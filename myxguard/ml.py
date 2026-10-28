"""Optional ONNX prompt-injection classifier.

The rules scanner does not need this. ``onnxruntime`` and ``tokenizers``
are imported only when a scan actually calls the model, and only after
``pip install "myxguard[ml]"``. Torch is not used at runtime.

The default weights are Protect AI's DeBERTa v3 prompt-injection model
(Apache-2.0). The first call downloads the ONNX file into the user cache.
Later calls stay offline. Set ``MYXGUARD_MODEL_PATH`` or
``ScanConfig.ml_model_path`` to a folder with ``model.onnx``,
``tokenizer.json``, and ``config.json`` to use a fine-tuned model instead.
"""

from __future__ import annotations

import json
import math
import os
import sys
import time
import urllib.request
from pathlib import Path
from typing import Optional

from myxguard.models import Finding, make_finding

# Verified on the Hugging Face model card (license: apache-2.0) and the
# repository tag. Labels in onnx/config.json are SAFE=0, INJECTION=1.
DEFAULT_MODEL_ID = "protectai/deberta-v3-base-prompt-injection-v2"
_HF_ONNX = (
    "https://huggingface.co/protectai/deberta-v3-base-prompt-injection-v2"
    "/resolve/main/onnx"
)
_ONNX_FILES = ("model.onnx", "tokenizer.json", "config.json")
_MAX_MODEL_CHARS = 8_000

# Seconds spent inside the last successful ONNX call. The benchmark reads
# this so it can report model time separately from the rule scan.
last_predict_seconds: Optional[float] = None

_SESSION: dict[str, object] = {}
_TOKENIZER: dict[str, object] = {}
_INJECTION_INDEX: dict[str, int] = {}


class MLNotInstalled(RuntimeError):
    """Raised when a scan asks for the classifier and the extra is missing."""


class MLModelError(RuntimeError):
    """Raised when the model files cannot be downloaded or read."""


def runtime_installed() -> bool:
    """True when both optional packages can be imported."""
    try:
        import onnxruntime  # noqa: F401
        import tokenizers  # noqa: F401
    except ImportError:
        return False
    return True


def injection_probability(text: str, model_path: Optional[str] = None) -> float:
    """Return the INJECTION probability for ``text``, from 0 to 1.

    Downloads the default model on first use when ``model_path`` and
    ``MYXGUARD_MODEL_PATH`` are both unset.
    """
    global last_predict_seconds
    _require_runtime()
    folder = ensure_model(model_path)
    started = time.perf_counter()
    probability = _run(text, folder)
    last_predict_seconds = time.perf_counter() - started
    return probability


def make_model_finding(text: str, probability: float) -> Finding:
    """Build the finding that shows the classifier probability."""
    if probability >= 0.75:
        severity = "critical"
    elif probability >= 0.5:
        severity = "high"
    elif probability >= 0.25:
        severity = "medium"
    else:
        severity = "low"
    percent = f"{probability:.3f}"
    return make_finding(
        text,
        0,
        len(text),
        rule_id="ml.prompt_injection",
        category="ml_classifier",
        severity=severity,
        explanation=(
            f"Classifier injection probability {percent}. "
            "The score keeps the rule score when that is higher, and otherwise "
            "uses the weighted blend of the rule score and this probability."
        ),
    )


def ensure_model(model_path: Optional[str] = None) -> Path:
    """Return a directory that contains the ONNX model and tokenizer.

    An explicit path, or ``MYXGUARD_MODEL_PATH``, must already be on disk.
    The default cache directory is filled from Hugging Face once.
    """
    explicit = model_path or os.environ.get("MYXGUARD_MODEL_PATH")
    if explicit:
        folder = Path(explicit).expanduser()
        missing = [name for name in _ONNX_FILES if not (folder / name).is_file()]
        if missing:
            names = ", ".join(missing)
            raise MLModelError(
                f"Model folder {folder} is missing {names}. "
                "Point MYXGUARD_MODEL_PATH or --ml-model at a folder with "
                "model.onnx, tokenizer.json, and config.json."
            )
        return folder
    folder = _cache_dir()
    if all((folder / name).is_file() for name in _ONNX_FILES):
        return folder
    _download_default(folder)
    return folder


def cache_size_bytes(model_path: Optional[str] = None) -> int:
    """Size of the three model files, or 0 when they are not on disk yet."""
    explicit = model_path or os.environ.get("MYXGUARD_MODEL_PATH")
    folder = Path(explicit).expanduser() if explicit else _cache_dir()
    total = 0
    for name in _ONNX_FILES:
        path = folder / name
        if path.is_file():
            total += path.stat().st_size
    return total


def _cache_dir() -> Path:
    root = os.environ.get("MYXGUARD_CACHE_DIR")
    base = Path(root).expanduser() if root else Path.home() / ".cache" / "myxguard"
    return base / "models" / "protectai-deberta-v3-base-prompt-injection-v2"


def _require_runtime() -> None:
    if runtime_installed():
        return
    raise MLNotInstalled(
        "The ML extra is not installed, so the classifier cannot run. "
        "The rules scanner still works without it. "
        'Install the extra with: pip install "myxguard[ml]" '
        "(onnxruntime and tokenizers; torch is not required at runtime)."
    )


def _download_default(folder: Path) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    # stderr, never stdout: the MCP server shares stdout with its client.
    print(
        "MyxGuard is downloading the ONNX classifier "
        f"({DEFAULT_MODEL_ID}) into {folder}. Later scans use this copy offline.",
        file=sys.stderr,
        flush=True,
    )
    for name in _ONNX_FILES:
        url = f"{_HF_ONNX}/{name}"
        destination = folder / name
        partial = folder / f"{name}.partial"
        try:
            _download(url, partial)
        except OSError as exc:
            if partial.exists():
                partial.unlink()
            raise MLModelError(
                f"Could not download {url}. Check the network and try again. {exc}"
            ) from exc
        partial.replace(destination)


def _download(url: str, destination: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "myxguard"})
    with urllib.request.urlopen(request, timeout=120) as response, destination.open("wb") as handle:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                return
            handle.write(chunk)


def _run(text: str, folder: Path) -> float:
    # Imported here so `import myxguard` stays free of onnxruntime.
    import numpy as np
    import onnxruntime as ort
    from tokenizers import Tokenizer

    key = str(folder.resolve())
    session = _SESSION.get(key)
    tokenizer = _TOKENIZER.get(key)
    if session is None or tokenizer is None:
        session = ort.InferenceSession(
            str(folder / "model.onnx"),
            providers=["CPUExecutionProvider"],
        )
        tokenizer = Tokenizer.from_file(str(folder / "tokenizer.json"))
        tokenizer.enable_truncation(max_length=512)
        _SESSION[key] = session
        _TOKENIZER[key] = tokenizer
        _INJECTION_INDEX[key] = _injection_index(folder / "config.json")
    assert isinstance(tokenizer, Tokenizer)
    piece = text[:_MAX_MODEL_CHARS]
    encoded = tokenizer.encode(piece)
    ids = encoded.ids or [0]
    mask = encoded.attention_mask or [1] * len(ids)
    feeds = {}
    for item in session.get_inputs():
        if item.name == "input_ids":
            feeds[item.name] = np.asarray([ids], dtype=np.int64)
        elif item.name == "attention_mask":
            feeds[item.name] = np.asarray([mask], dtype=np.int64)
        elif item.name == "token_type_ids":
            feeds[item.name] = np.zeros((1, len(ids)), dtype=np.int64)
        else:
            raise MLModelError(
                f"This ONNX model has an input named {item.name!r} that MyxGuard "
                "does not fill. Export with input_ids and attention_mask."
            )
    outputs = session.run(None, feeds)
    if not outputs:
        raise MLModelError("The ONNX model returned no outputs.")
    logits = outputs[0][0]
    values = [float(item) for item in logits]
    if not values:
        raise MLModelError("The ONNX model returned an empty score vector.")
    probabilities = _softmax(values)
    index = _INJECTION_INDEX[key]
    if index < 0 or index >= len(probabilities):
        raise MLModelError(
            f"config.json injection label index {index} does not match "
            f"a model with {len(probabilities)} labels."
        )
    return probabilities[index]


def _injection_index(config_path: Path) -> int:
    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MLModelError(f"Could not read {config_path}.") from exc
    mapping = payload.get("id2label") or {}
    for key, label in mapping.items():
        if str(label).strip().upper() == "INJECTION":
            return int(key)
    label_to_id = payload.get("label2id") or {}
    for label, index in label_to_id.items():
        if str(label).strip().upper() == "INJECTION":
            return int(index)
    # The published ProtectAI card uses this order. A custom model should
    # still set id2label so this fallback is not the thing you rely on.
    return 1


def _softmax(values: list[float]) -> list[float]:
    peak = max(values)
    shifted = [math.exp(item - peak) for item in values]
    total = sum(shifted)
    if total <= 0:
        raise MLModelError("Could not turn model logits into probabilities.")
    return [item / total for item in shifted]
