# Changelog

## 0.4.0 — 2026-10-26

- `datasets/train/train.jsonl` is a training corpus of about 2,600 rows (English, German, French, Italian, Swiss German), roughly half attacks and half benign text. Benign rows emphasise hard negatives: everyday chat, email, support, recipes, code, code comments, logs, base64 images, security write-ups that quote an injection, and “ignore the previous email”.
- Sources are limited to MIT, Apache-2.0, CC-BY, and CC0. Public rows come from Tatoeba (CC BY 2.0 FR), `deepset/prompt-injections` (Apache-2.0), `neuralchemy/Prompt-injection-dataset` (Apache-2.0 slices only), `hackaprompt/hackaprompt-dataset` (MIT), `3nesdeniz/english-prompt-injection-3k` (CC-BY-4.0), and `Shomi28/prompt-injection-dataset` (MIT). The rest is original text, source `myxguard-train-original`. Research-only and non-commercial slices were skipped. Details are in `THIRD_PARTY_NOTICES.md`.
- The build drops exact and near-duplicate text from `datasets/eval/heldout.jsonl` and from `datasets/dev/dev.jsonl`. Dev stays the validation split. `training/finetune.py` now defaults to that train file and to dev for validation.
- `python scripts/dataset_stats.py` prints counts by language, label, category, and source.
- `python training/finetune.py --smoke` checks the train/export path on CPU with a tiny random model. It is not a usable detector. The real run is still the Colab steps in `training/README.md`.

## 0.3.0 — 2026-10-26

- Optional extra `myxguard[ml]` (`onnxruntime` and `tokenizers`). The default install stays free of dependencies, and `scan(text)` does not load the classifier.
- Default model: `protectai/deberta-v3-base-prompt-injection-v2` (Apache-2.0). ONNX weights download into the user cache on first use, then run offline. `MYXGUARD_MODEL_PATH` or `--ml-model` points at a local folder so a later fine-tune can replace it. Meta Prompt Guard is not used.
- Rules run first. A high rule score skips the model. Otherwise the score is the higher of the rule score and a weighted blend of that score with the injection probability. The result includes an `ml.prompt_injection` finding with the probability.
- CLI `--ml` / `--ml-model`, and MCP `scan_text` arguments `ml` and `ml_model_path`.
- `python scripts/benchmark.py --ml --eval` prints rules-only and rules-plus-classifier tables, plus mean CPU latency per text.
- `training/` documents a fine-tune of `xlm-roberta-base` (MIT) or `microsoft/mdeberta-v3-base` (MIT), with German, French, Italian, and Swiss German augmentation, an ONNX export, and Colab steps. `datasets/eval/heldout.jsonl` is refused and its texts are removed from the training rows. No training run ships with this release.
- Held-out measurement with the default 0.5/0.5 blend, threshold 25: rules-only recall 0.425 and false-positive rate 0; rules plus the Protect AI classifier recall 0.989 and false-positive rate 0.250. The classifier was not tuned on that file. CPU median for a classifier call was about 21 ms after the weights were cached (747 MB download).

## 0.2.0 — 2026-10-26

- Phrase packs allow a short filler (`Sie`, `bitte`, `donc`, `pure`, `eifach`, and similar) between the verb and the object, and they accept more nouns.
- A discussion cue after a quotation lowers the hit, and a match on a `#`, `//`, or SQL `--` line is lowered too. HTML comments stay at full strength.
- A plain `System` / `User` / `Assistant` log is not a finding. It counts only when one of those lines is itself an instruction.
- `\xHH`, `\uHHHH`, and `\UHHHHHHHH` escapes are decoded before the phrase and intent scan.
- New intent detector: override verbs, task nouns, and "earlier" words score together inside a sliding window, after accent and apostrophe folding. Exfiltration, role change, and tool-confirmation phrases use their own pairs. Hidden HTML and a mail note addressed to the model raise the severity by one step. A verb plus a noun, with no "earlier" word, stays low.
- `ScanConfig` sets the severity weights and the intent window. `scan(text)` without `config` behaves as before.
- `datasets/dev/dev.jsonl` is an original dev set for tuning. `datasets/eval/heldout.jsonl` is still not used to write rules.
- The German "send the password" rule ignores a reset link (`Passwort zum Zurücksetzen`, `zruggsetze`).
- Held-out recall at threshold 25 moved from 0.108 to 0.425 (79 of 186 attacks). The false-positive rate moved from 0.027 to 0 (0 of 184 benign rows). That file was not used to tune the rules.

## 0.1.0 — 2026-10-26

First release. Not published on PyPI.

- `scan` and `scan_file` return a score from 0 to 100, a risk level, and findings with rule id, category, severity, span, and offsets.
- Detectors for hidden Unicode, hidden HTML (`html.parser`), phrase packs (English, German, French, Italian, Swiss German), one-level obfuscation (Base64, hex, ROT13, leetspeak, spaced letters, percent-encoding, HTML entities), and fake chat delimiters.
- CLI: `myxguard check <file|->` with `--json`, `--threshold`, `--content-type`, `--languages`, and colour when stdout is a terminal.
- MCP stdio server (standard-library JSON-RPC) with the `scan_text` tool.
- Regression dataset, benchmark script, and pytest suite.
- Phrase ideas adapted from prompt-guard (MIT) and vigil-llm (Apache-2.0) are recorded in `THIRD_PARTY_NOTICES.md`. Italian and Swiss German packs are original.
- Held-out eval set in `datasets/eval/heldout.jsonl` (not used to tune rules). `python scripts/benchmark.py datasets/eval/heldout.jsonl --eval` reports precision, recall, F1, and false-positive rate per language and per category. The regression table is unchanged.
- German cmd walkthrough in `tests/manual_examples.md`.
