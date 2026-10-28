"""A tiny MCP server over stdio, using only the standard library.

The wire format is the same one Cursor and Claude Desktop use: each
JSON-RPC message is prefixed with a ``Content-Length`` header, like the
Language Server Protocol. A single JSON line is also accepted so the
server is easy to try by hand.

The only tool is ``scan_text``. It returns the same object as
:func:`myxguard.scan`, encoded as JSON text.
"""

from __future__ import annotations

import json
import sys
from typing import Any, BinaryIO, Optional

from myxguard import __version__
from myxguard.ml import MLModelError, MLNotInstalled
from myxguard.scanner import scan
from myxguard.scoring import ScanConfig

_PROTOCOL_VERSION = "2024-11-05"
_SERVER_INFO = {"name": "myxguard", "version": __version__}

_SCAN_TEXT_TOOL = {
    "name": "scan_text",
    "description": (
        "Scan text for prompt-injection signals: hidden Unicode, hidden HTML, "
        "instruction-override phrases in English, German, French, Italian, and "
        "Swiss German, obfuscation (Base64, hex, ROT13, leetspeak, spaced letters), "
        "and fake chat delimiters. Returns a risk score from 0 to 100, a risk level "
        "(none, low, medium, high, critical), and findings. This is a heuristic, "
        "not a complete defense."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "The text to scan."},
            "content_type": {
                "type": "string",
                "enum": ["text", "html", "auto"],
                "description": "How to read the text. Defaults to auto.",
            },
            "languages": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Language codes to enable, for example ['de', 'fr']. Omit to use all.",
            },
            "ml": {
                "type": "boolean",
                "description": (
                    "When true, run the optional ONNX classifier if the rule score "
                    "is below high. Requires the myxguard[ml] extra."
                ),
            },
            "ml_model_path": {
                "type": "string",
                "description": (
                    "Folder with model.onnx, tokenizer.json, and config.json. "
                    "Turns the classifier on."
                ),
            },
        },
        "required": ["text"],
        "additionalProperties": False,
    },
}


def serve(stdin: Optional[BinaryIO] = None, stdout: Optional[BinaryIO] = None) -> None:
    """Read MCP messages until stdin closes. Logs go to stderr, never stdout."""
    incoming = stdin if stdin is not None else sys.stdin.buffer
    outgoing = stdout if stdout is not None else sys.stdout.buffer
    while True:
        try:
            message = read_message(incoming)
        except ValueError as exc:
            write_message(
                outgoing,
                _error(None, -32700, f"Parse error: {exc}"),
            )
            continue
        if message is None:
            return
        response = handle_message(message)
        if response is not None:
            write_message(outgoing, response)


def handle_message(message: Any) -> Optional[dict[str, Any]]:
    """Answer one JSON-RPC message. Notifications return ``None``."""
    if not isinstance(message, dict):
        return _error(None, -32600, "Request must be a JSON object.")
    method = message.get("method")
    if not isinstance(method, str):
        return _error(message.get("id"), -32600, "Request is missing a method.")
    has_id = "id" in message and message["id"] is not None
    request_id = message.get("id")
    params = message.get("params") or {}
    if params is None:
        params = {}
    if not isinstance(params, dict):
        if has_id:
            return _error(request_id, -32602, "Params must be an object.")
        return None

    if method in {"notifications/initialized", "initialized", "notifications/cancelled"}:
        return None

    if not has_id:
        # A notification we do not handle. There is nothing to send back.
        return None

    if method == "initialize":
        # Answer with the protocol version this server implements.
        # Clients that speak it will continue; others should disconnect.
        return _result(
            request_id,
            {
                "protocolVersion": _PROTOCOL_VERSION,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": _SERVER_INFO,
            },
        )
    if method == "ping":
        return _result(request_id, {})
    if method == "tools/list":
        return _result(request_id, {"tools": [_SCAN_TEXT_TOOL]})
    if method == "prompts/list":
        return _result(request_id, {"prompts": []})
    if method == "resources/list":
        return _result(request_id, {"resources": []})
    if method == "tools/call":
        return _result(request_id, _call_tool(params))
    return _error(request_id, -32601, f"Method not found: {method}")


def _call_tool(params: dict[str, Any]) -> dict[str, Any]:
    name = params.get("name")
    arguments = params.get("arguments") or {}
    if name != "scan_text":
        return _tool_error(f"Unknown tool: {name}")
    if not isinstance(arguments, dict):
        return _tool_error("arguments must be an object.")
    text = arguments.get("text")
    if not isinstance(text, str):
        return _tool_error("text must be a string.")
    content_type = arguments.get("content_type", "auto")
    if not isinstance(content_type, str):
        return _tool_error("content_type must be a string.")
    languages = arguments.get("languages")
    if isinstance(languages, str):
        languages = [part.strip() for part in languages.split(",") if part.strip()]
    if languages is not None and not isinstance(languages, list):
        return _tool_error("languages must be a list of language codes.")
    use_ml = arguments.get("ml", False)
    model_path = arguments.get("ml_model_path")
    if model_path is not None and not isinstance(model_path, str):
        return _tool_error("ml_model_path must be a string.")
    if not isinstance(use_ml, bool):
        return _tool_error("ml must be true or false.")
    config = None
    if use_ml or model_path:
        config = ScanConfig(ml=True, ml_model_path=model_path)
    try:
        result = scan(text, content_type=content_type, languages=languages, config=config)
    except (TypeError, ValueError, MLNotInstalled, MLModelError) as exc:
        return _tool_error(str(exc))
    return {
        "content": [
            {
                "type": "text",
                "text": result.to_json(),
            }
        ],
        "isError": False,
    }


def read_message(stream: BinaryIO) -> Optional[dict[str, Any]]:
    """Read one framed message, or one JSON line. ``None`` means EOF."""
    first = stream.readline()
    if first == b"":
        return None
    stripped = first.lstrip()
    if stripped.startswith(b"{"):
        return json.loads(stripped.decode("utf-8"))

    headers = {}
    _absorb_header(headers, first)
    while True:
        line = stream.readline()
        if line in (b"\r\n", b"\n", b""):
            break
        _absorb_header(headers, line)
    if "content-length" not in headers:
        raise ValueError("Missing Content-Length header.")
    length = int(headers["content-length"])
    if length < 0:
        raise ValueError("Content-Length must be positive.")
    body = stream.read(length)
    if len(body) < length:
        raise ValueError("Unexpected end of stream.")
    return json.loads(body.decode("utf-8"))


def write_message(stream: BinaryIO, payload: dict[str, Any]) -> None:
    """Write one ``Content-Length`` framed JSON-RPC message."""
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    header = f"Content-Length: {len(body)}\r\n\r\n".encode("ascii")
    stream.write(header)
    stream.write(body)
    stream.flush()


def _absorb_header(headers: dict[str, str], line: bytes) -> None:
    if b":" not in line:
        return
    name, value = line.split(b":", 1)
    headers[name.decode("ascii", errors="replace").strip().lower()] = value.decode(
        "ascii", errors="replace"
    ).strip()


def _result(request_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": code, "message": message},
    }


def _tool_error(message: str) -> dict[str, Any]:
    return {
        "content": [{"type": "text", "text": message}],
        "isError": True,
    }
