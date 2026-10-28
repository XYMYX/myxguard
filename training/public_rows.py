"""Load openly licensed public rows for the training corpus.

Licenses were checked on the dataset cards before a source was allowed in.
Research-only slices (WildGuard), HarmBench behavior prompts, and rows that
ask for weapons or hate are left out. Nothing from datasets/eval is read here.
"""

from __future__ import annotations

import json
import random
import re
import urllib.request
from collections import defaultdict
from pathlib import Path
from typing import Optional

# Hugging Face dataset files. The Hub license tag was checked on 2026-10-26.
_DATASETS = {
    "deepset": (
        "https://huggingface.co/datasets/deepset/prompt-injections/resolve/main/"
        "data/train-00000-of-00001-9564e8b05b4757ab.parquet"
    ),
    "deepset_test": (
        "https://huggingface.co/datasets/deepset/prompt-injections/resolve/main/"
        "data/test-00000-of-00001-701d16158af87368.parquet"
    ),
    "neuralchemy": (
        "https://huggingface.co/datasets/neuralchemy/Prompt-injection-dataset/"
        "resolve/main/core/train-00000-of-00001.parquet"
    ),
    "enes": (
        "https://huggingface.co/datasets/3nesdeniz/english-prompt-injection-3k/"
        "resolve/main/data/train.parquet"
    ),
    "shomi": (
        "https://huggingface.co/datasets/Shomi28/prompt-injection-dataset/"
        "resolve/main/data/train-00000-of-00001.parquet"
    ),
}

_TATOEBA_LANG = {
    "en": "eng",
    "de": "deu",
    "fr": "fra",
    "it": "ita",
    "gsw": "gsw",
}

# Skip weapons, hate, and propaganda. A prompt-injection corpus does not need them.
_UNSAFE = re.compile(
    r"(?i)("
    r"\b(bomb|bombs|explosive|explosives|methamphetamine)\b|"
    r"nerve agent|chloramine|improvised explosive|pipe bomb|"
    r"\b(hitler|nazi|nazis)\b|uyghur|uigur|uighur|"
    r"credit card fraud|child sexual|"
    r"\b(fuck|shit|merde|putain|schei[sß])\b"
    r")"
)
_POLITICS = re.compile(
    r"(?i)("
    r"xi jinping|sebastian kurz|zeit online|der spiegel|"
    r"fl[uü]chtling|refugee crisis|unelectable|unw[aä]hlbar|"
    r"gr[uü]nen|manifesto|colonial gentleman|gutherren|"
    r"christentum|christianity so important|destroy humanity"
    r")"
)
_INJECTION_CUE = re.compile(
    r"(?i)("
    r"ignore|disregard|forget|vergiss|ignorier|"
    r"previous instruction|vorherig|bisherig|"
    r"system prompt|prompt text|prompt-texte|jailbreak|"
    r"do anything now|new task|neue aufgabe|"
    r"override|pwned|reveal your|show me all your prompt|"
    r"anweisungen"
    r")"
)

_NEURAL_CATEGORY = {
    "direct_injection": "instruction_override",
    "instruction_override": "instruction_override",
    "prompt_injection": "instruction_override",
    "system_manipulation": "instruction_override",
    "control": "instruction_override",
    "output_manipulation": "instruction_override",
    "response_manipulation": "instruction_override",
    "adversarial": "instruction_override",
    "jailbreak": "jailbreak_persona",
    "persona_replacement": "jailbreak_persona",
    "many_shot": "jailbreak_persona",
    "crescendo": "jailbreak_persona",
    "system_extraction": "data_exfiltration",
    "prompt_extraction": "data_exfiltration",
    "prompt_leak": "data_exfiltration",
    "prompt_leaking": "data_exfiltration",
    "training_extraction": "data_exfiltration",
    "model_fingerprinting": "data_exfiltration",
    "encoding_obfuscation": "obfuscation",
    "encoding": "obfuscation",
    "token_smuggling": "hidden_unicode",
    "token_injection": "hidden_unicode",
    "indirect_injection": "indirect_injection",
    "payload_injection": "indirect_injection",
    "rag_poisoning": "indirect_injection",
    "multi_turn": "indirect_injection",
    "agent_manipulation": "tool_abuse",
    "code_execution": "tool_abuse",
    "context_confusion": "delimiter_injection",
    "benign": "hard_negative",
    "edge_case": "hard_negative",
}

_ENES_CATEGORY = {
    "instruction_override": "instruction_override",
    "system_prompt_extraction": "data_exfiltration",
    "delimiter_format_injection": "delimiter_injection",
    "payload_splitting": "obfuscation",
    "data_exfiltration": "data_exfiltration",
    "jailbreak_persona": "jailbreak_persona",
    "obfuscation_encoding": "obfuscation",
    "refusal_suppression": "jailbreak_persona",
    "benign": "hard_negative",
}


def cache_dir(root: Path) -> Path:
    path = root / "training" / ".cache"
    path.mkdir(parents=True, exist_ok=True)
    return path


def ensure_parquet(root: Path, key: str) -> Path:
    """Download one dataset file into the local cache if it is not there yet."""
    destination = cache_dir(root) / f"{key}.parquet"
    if destination.is_file() and destination.stat().st_size > 0:
        return destination
    _download(_DATASETS[key], destination)
    return destination


def load_public(
    tables: dict[str, list[dict]],
    rng: random.Random,
) -> tuple[list[dict[str, str]], dict[str, int]]:
    """Return capped public rows and a count of rows that were skipped.

    ``tables`` maps a dataset key to rows already read from the parquet cache.
    Tatoeba is fetched here over HTTPS. DuckDB stays in the build script.
    """
    skipped = {
        "unsafe": 0,
        "politics": 0,
        "not_injection": 0,
        "research_or_harmbench": 0,
        "unlicensed_source": 0,
    }
    rows: list[dict[str, str]] = []
    rows.extend(_deepset(tables["deepset"] + tables["deepset_test"], skipped))
    rows.extend(_neuralchemy(tables["neuralchemy"], rng, skipped))
    rows.extend(_enes(tables["enes"], rng, skipped))
    rows.extend(_shomi(tables["shomi"], rng, skipped))
    rows.extend(fetch_tatoeba(rng, skipped))
    return rows, skipped


def fetch_tatoeba(rng: random.Random, skipped: dict[str, int]) -> list[dict[str, str]]:
    """Everyday sentences. CC BY 2.0 FR, one owner per row, fixed random seed."""
    chosen: list[dict[str, str]] = []
    for language, code in _TATOEBA_LANG.items():
        want = 100 if language == "gsw" else 80
        got: list[dict[str, str]] = []
        url: Optional[str] = (
            "https://api.tatoeba.org/unstable/sentences"
            f"?lang={code}&limit=100&sort=random:20261026"
        )
        pages = 0
        while url and pages < 12 and len(got) < want:
            pages += 1
            payload = _get_json(url)
            for item in payload.get("data", []):
                if item.get("is_unapproved"):
                    continue
                if item.get("license") != "CC BY 2.0 FR":
                    skipped["unlicensed_source"] += 1
                    continue
                text = str(item.get("text") or "").strip()
                words = text.split()
                if len(words) < 4 or len(words) > 22:
                    continue
                if _UNSAFE.search(text):
                    skipped["unsafe"] += 1
                    continue
                owner = str(item.get("owner") or "unknown")
                got.append(
                    {
                        "text": text,
                        "label": "benign",
                        "language": language,
                        "category": "everyday",
                        "source": f"tatoeba.org:{item.get('id')}:{owner}",
                        "license": "CC-BY-2.0-FR",
                    }
                )
                if len(got) >= want:
                    break
            paging = payload.get("paging") or {}
            url = paging.get("next") if paging.get("has_next") else None
        rng.shuffle(got)
        chosen.extend(got[:want])
    return chosen


def _deepset(records: list[dict], skipped: dict[str, int]) -> list[dict[str, str]]:
    rows = []
    for record in records:
            text = str(record.get("text") or "").strip()
            label_bit = int(record.get("label") or 0)
            if not text or _blocked(text, skipped):
                continue
            if label_bit == 1 and not _INJECTION_CUE.search(text):
                # deepset marks some ordinary or political tasks as positive.
                skipped["not_injection"] += 1
                continue
            if label_bit == 0 and (_INJECTION_CUE.search(text) or len(text.split()) < 6):
                skipped["not_injection"] += 1
                continue
            rows.append(
                {
                    "text": text,
                    "label": "malicious" if label_bit == 1 else "benign",
                    "language": _guess_lang(text),
                    "category": _deepset_category(text, label_bit),
                    "source": "deepset/prompt-injections",
                    "license": "Apache-2.0",
                }
            )
    return rows


def _neuralchemy(
    records: list[dict],
    rng: random.Random,
    skipped: dict[str, int],
) -> list[dict[str, str]]:
    grouped: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for record in records:
        source = str(record.get("source") or "")
        if source in {"wildguard_judgecomp", "harmbench", "harmbench_benign"}:
            skipped["research_or_harmbench"] += 1
            continue
        if source not in {"original", "neuralchemy_v1", "hackaprompt"}:
            skipped["unlicensed_source"] += 1
            continue
        text = str(record.get("text") or "").strip()
        if not text or _blocked(text, skipped):
            continue
        label_bit = int(record.get("label") or 0)
        if label_bit == 1 and source == "hackaprompt" and len(text) > 900:
            continue
        category = _NEURAL_CATEGORY.get(str(record.get("category") or ""), "")
        if not category:
            category = "instruction_override" if label_bit == 1 else "hard_negative"
        if source == "hackaprompt":
            our_source = "hackaprompt/hackaprompt-dataset"
            license_name = "MIT"
        else:
            our_source = "neuralchemy/Prompt-injection-dataset"
            license_name = "Apache-2.0"
        grouped[(source, "malicious" if label_bit == 1 else "benign")].append(
            {
                "text": text,
                "label": "malicious" if label_bit == 1 else "benign",
                "language": "en",
                "category": category,
                "source": our_source,
                "license": license_name,
            }
        )
    caps = {
        ("original", "benign"): 20,
        ("original", "malicious"): 60,
        ("neuralchemy_v1", "benign"): 70,
        ("neuralchemy_v1", "malicious"): 70,
        ("hackaprompt", "malicious"): 50,
        ("hackaprompt", "benign"): 0,
    }
    chosen: list[dict[str, str]] = []
    for key, cap in caps.items():
        bucket = grouped.get(key, [])
        rng.shuffle(bucket)
        chosen.extend(_diverse(bucket, cap, rng))
    return chosen


def _enes(
    records: list[dict],
    rng: random.Random,
    skipped: dict[str, int],
) -> list[dict[str, str]]:
    by_family: dict[str, list[dict[str, str]]] = defaultdict(list)
    for record in records:
        text = str(record.get("text") or "").strip()
        if not text or _blocked(text, skipped):
            continue
        family = str(record.get("attack_family") or "benign")
        category = _ENES_CATEGORY.get(family)
        if category is None:
            skipped["unlicensed_source"] += 1
            continue
        label_bit = int(record.get("label") or 0)
        by_family[family].append(
            {
                "text": text,
                "label": "malicious" if label_bit == 1 else "benign",
                "language": "en",
                "category": category,
                "source": "3nesdeniz/english-prompt-injection-3k",
                "license": "CC-BY-4.0",
            }
        )
    chosen: list[dict[str, str]] = []
    benign = by_family.get("benign", [])
    rng.shuffle(benign)
    chosen.extend(_diverse(benign, 100, rng))
    for family, bucket in by_family.items():
        if family == "benign":
            continue
        rng.shuffle(bucket)
        chosen.extend(_diverse(bucket, 24, rng))
    return chosen


def _shomi(
    records: list[dict],
    rng: random.Random,
    skipped: dict[str, int],
) -> list[dict[str, str]]:
    buckets: dict[str, list[dict[str, str]]] = {"benign": [], "malicious": []}
    for record in records:
        text = str(record.get("text") or "").strip()
        if not text or _blocked(text, skipped):
            continue
        label_bit = int(record.get("label") or 0)
        label = "malicious" if label_bit == 1 else "benign"
        buckets[label].append(
            {
                "text": text,
                "label": label,
                "language": "en",
                "category": _keyword_category(text, label),
                "source": "Shomi28/prompt-injection-dataset",
                "license": "MIT",
            }
        )
    chosen: list[dict[str, str]] = []
    for label, cap in (("benign", 50), ("malicious", 50)):
        rng.shuffle(buckets[label])
        chosen.extend(_diverse(buckets[label], cap, rng))
    return chosen


def _diverse(rows: list[dict[str, str]], cap: int, rng: random.Random) -> list[dict[str, str]]:
    """Round-robin categories so one template family does not fill the cap."""
    if cap <= 0:
        return []
    by_category: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_category[row["category"]].append(row)
    for bucket in by_category.values():
        rng.shuffle(bucket)
    chosen: list[dict[str, str]] = []
    names = list(by_category)
    while len(chosen) < cap and any(by_category.values()):
        for name in names:
            bucket = by_category[name]
            if not bucket:
                continue
            chosen.append(bucket.pop())
            if len(chosen) >= cap:
                break
    return chosen


def _blocked(text: str, skipped: dict[str, int]) -> bool:
    if _UNSAFE.search(text):
        skipped["unsafe"] += 1
        return True
    if _POLITICS.search(text):
        skipped["politics"] += 1
        return True
    return False


def _deepset_category(text: str, label_bit: int) -> str:
    if label_bit == 0:
        return "everyday"
    return _keyword_category(text, "malicious")


def _keyword_category(text: str, label: str) -> str:
    if label == "benign":
        return "hard_negative" if _INJECTION_CUE.search(text) else "everyday"
    lowered = text.lower()
    if any(word in lowered for word in ("system prompt", "prompt text", "prompt-texte", "api key")):
        return "data_exfiltration"
    if any(word in lowered for word in ("dan", "jailbreak", "you are now", "du bist jetzt")):
        return "jailbreak_persona"
    if "base64" in lowered or "rot13" in lowered:
        return "obfuscation"
    return "instruction_override"


def _guess_lang(text: str) -> str:
    lowered = text.lower()
    german = len(
        re.findall(
            r"\b(und|die|der|nicht|bitte|ich|ist|ein|eine|auf|mit|für|dass|vergiss|ignorieren)\b",
            lowered,
        )
    )
    german += len(re.findall(r"[äöüß]", lowered))
    french = len(re.findall(r"\b(le|la|les|vous|une|dans|pour|avec|bonjour|ignorez)\b", lowered))
    if german >= 2 and german > french:
        return "de"
    if french >= 2 and french > german:
        return "fr"
    return "en"


def _download(url: str, destination: Path) -> None:
    temporary = destination.with_suffix(".partial")
    request = urllib.request.Request(url, headers={"User-Agent": "myxguard-corpus"})
    with urllib.request.urlopen(request, timeout=120) as response:
        temporary.write_bytes(response.read())
    temporary.replace(destination)


def _get_json(url: str) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": "myxguard-corpus"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))
