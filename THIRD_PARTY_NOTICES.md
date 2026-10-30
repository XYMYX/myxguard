# Third-party notices

MyxGuard is MIT, Copyright (c) 2026 XYMYX. See [LICENSE](LICENSE).

This file lists every outside project that was read while building version 0.1, whether or not code or text was copied. Licenses were checked against the upstream license files before anything was adapted.

## Adapted into this tree

### prompt-guard

- Project: prompt-guard
- Source: https://github.com/seojoonkim/prompt-guard
- License: MIT
- Copyright: Copyright (c) 2026 Seojoon Kim
- What we used: multilingual regular expressions in `prompt_guard/patterns.py` (English, German, and French instruction, role, jailbreak, and exfiltration phrases).
- What changed: the expressions were narrowed so everyday sentences do not match, rewritten as bounded patterns (no `.*`), stored as JSON in `myxguard/data/patterns/en.json`, `de.json`, `fr.json`, and parts of `common.json`, and given a `benign_example` each. Broad social-engineering phrases and the other languages in that file (including Korean, Japanese, and Chinese) were not copied. Italian (`it.json`) and Swiss German (`gsw.json`) are original. The discussion downgrade in `myxguard/context.py` is original. The obfuscation detector follows the same idea as that project's decoder (Base64, hex, ROT13, leetspeak, spaced letters) but the code is new: one decode level, and a hit is reported only when the decoded text matches a phrase rule. Percent-encoding and HTML numeric entities were added here.

The MIT license requires this notice:

```
MIT License

Copyright (c) 2026 Seojoon Kim

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

### vigil-llm

- Project: vigil-llm
- Source: https://github.com/deadbits/vigil-llm
- License: Apache-2.0
- Copyright: Adam M. Swanda
- Upstream files consulted: `data/yara/instruction_bypass.yar`, `data/yara/mdexfil.yar`, `data/yara/system_instructions.yar`, `data/yara/react.yar`
- What changed: selected YARA strings were rewritten as bounded regular expressions in `myxguard/data/patterns/common.json` and `en.json` (instruction-bypass wording, markdown image exfiltration, chat-template markers such as `<|im_start|>` and `[INST]`). The markdown rule requires a query that names a secret, token, password, API key, or prompt, so a normal cache-busting query does not match. The ReAct Thought/Observation rule was not ported, because it matches ordinary agent traces. No YARA engine is included.

The rewritten expressions live in `myxguard/data/patterns/common.json` and `en.json` (`_meta.adapted_from` says they were modified). `myxguard/detectors/patterns.py` and `myxguard/detectors/delimiters.py` point at that rewrite in their module docstrings. `myxguard/detectors/obfuscation.py` is not a Vigil derivative. It is described under prompt-guard above.

The Apache-2.0 license text is in [LICENSES/Apache-2.0.txt](LICENSES/Apache-2.0.txt).

### deepset/prompt-injections

- Project: prompt-injections
- Source: https://huggingface.co/datasets/deepset/prompt-injections
- License: Apache-2.0
- Copyright: deepset (dataset card and the LICENSE file added to the dataset)
- What we used: eight short rows, stored in `datasets/deepset_sample.jsonl`. Label `1` was mapped to `malicious` and label `0` to `benign`. The four malicious rows are the "forget previous tasks / ignore the above instructions" family. The four benign rows are ordinary questions (programming courses, bestsellers, travel vaccinations, a restaurant in Munich). Rows with hateful or political content were not included. The parquet file was not copied.
- What changed: field names are MyxGuard's JSONL schema (`text`, `label`, `language`, `category`, `source`). `source` is `deepset/prompt-injections`.

The Apache-2.0 license text that covers this subset is the same file: [LICENSES/Apache-2.0.txt](LICENSES/Apache-2.0.txt).

## Consulted, not copied

### llm-guard

- Project: llm-guard
- Source: https://github.com/protectai/llm-guard
- License: MIT
- Copyright: Copyright (c) Protect AI
- What we read: `llm_guard/input_scanners/invisible_text.py`, which flags characters in Unicode categories Cf, Co, and Cn.
- What we did: no code and no character list was copied. `myxguard/detectors/unicode_hidden.py` names specific characters (zero-width, bidi overrides, tag characters, variation selectors) so ordinary Arabic and Hebrew formatting is not flagged. The module docstring records that the idea was consulted.

### arc_pi_taxonomy

- Project: arc_pi_taxonomy
- Source: https://github.com/Arcanum-Sec/arc_pi_taxonomy
- License: CC-BY-4.0 (the repository `LICENSE.md`; the GitHub API SPDX field was `NOASSERTION`)
- Copyright: Copyright 2024–2026 Jason Haddix, Arcanum Information Security
- What we did: the taxonomy was read as orientation for category names such as instruction override and exfiltration. No taxonomy text, taxonomy tables, or example prompts were copied.

If you describe MyxGuard's category set as informed by that work, use their credit line: "based on Arcanum Prompt Injection Taxonomy by Jason Haddix."

### agent-threat-rules

- Project: https://github.com/Agent-Threat-Rule/agent-threat-rules
- License: MIT
- What we did: not copied. No rules, no `data/pint-benchmark` rows, and none of that project's names are used in MyxGuard's branding or rule ids.

## Held-out eval set (`datasets/eval/heldout.jsonl`)

These rows were not used to write or tune the rules. The file also contains original sentences by XYMYX (MIT, source `myxguard-eval-original`): paraphrases, indirect mail, hidden HTML, unicode tricks, encodings, recipes, support questions, and other benign lookalikes. Those original sentences are not third-party material.

### Tatoeba

- Source: https://tatoeba.org
- License: CC BY 2.0 FR (each included sentence reports this license from the Tatoeba API)
- What we used: 88 everyday sentences in English, German, French, Italian, and Swiss German
- Attribution: the `source` field is `tatoeba.org:<sentence id>:<username>`. Copyright stays with those contributors. Terms: https://tatoeba.org/en/terms_of_use

### deepset/prompt-injections (additional rows)

- Same project and Apache-2.0 license as the eight-row sample above
- What changed: 50 further rows, chosen because they are ordinary questions or prompt-injection attempts. Rows already stored in `datasets/deepset_sample.jsonl` are not repeated. Hate, slurs, and party-propaganda rows were left out. Labels follow the dataset (`1` malicious, `0` benign) only for the rows we kept. Ordinary task prompts that deepset marks positive but that are not injection attempts were not copied, so the eval is not a dump of the whole file.

### neuralchemy/Prompt-injection-dataset

- Source: https://huggingface.co/datasets/neuralchemy/Prompt-injection-dataset
- License: Apache-2.0 (dataset card and README)
- What we used: 28 rows from the `core` / `test` split whose `source` is `original` or `neuralchemy_v1` (the project's own Apache-2.0 material): benign hard negatives such as "Ignore the previous meeting notes…" and injection attempts that are not shell payloads.
- What we did not copy: rows with `source` `wildguard_judgecomp` (described on the card as research-only) and HarmBench rows. HarmBench itself is MIT, but those rows are harmful-behavior prompts (crime and abuse), not prompt-injection examples, so they are not in this tree.

The Apache-2.0 text that covers this subset is [LICENSES/Apache-2.0.txt](LICENSES/Apache-2.0.txt).

### hackaprompt/hackaprompt-dataset

- Source: https://huggingface.co/datasets/hackaprompt/hackaprompt-dataset
- License: MIT (dataset card on that page; checked 2026-10-26)
- Copyright: HackAPrompt contributors. The card does not print a separate copyright year. Cite Schulhoff et al., "Ignore This Title and HackAPrompt", EMNLP 2023.
- What we used: 16 competition prompts. The upstream file server returned 401, so the text was taken from `neuralchemy/Prompt-injection-dataset` rows whose `source` field is `hackaprompt` (NeurAlchemy's card also redistributes that data). We record the HackAPrompt MIT license, which is the stricter attribution, and the NeurAlchemy Apache-2.0 redistribution above.
- What changed: nothing inside the prompt strings. Long and offensive submissions were not selected.

The MIT license requires this notice:

```
MIT License

Copyright (c) HackAPrompt contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

NeurAlchemy's dataset card calls the HackAPrompt slice "CC BY 4.0". The official HackAPrompt dataset card says MIT. This tree follows the official card.

## Original dev text

`datasets/dev/dev.jsonl` is original text written for this package (source `myxguard-dev-original`). License: MIT, copyright XYMYX, same terms as `LICENSE`. It is not copied from the held-out file or from the third-party datasets above.

## Training corpus (`datasets/train/train.jsonl`)

Built 2026-10-26. About 2,576 rows. Licenses on the rows are MIT, Apache-2.0, CC-BY-4.0, or CC BY 2.0 FR. The build refuses `datasets/eval/heldout.jsonl` and drops exact and near-duplicate text from that file and from `datasets/dev/dev.jsonl`. Dev is validation only.

Checked and skipped, so they are not in the file:

- NeurAlchemy rows whose `source` is `wildguard_judgecomp` (the card calls that slice research-only).
- HarmBench rows in the same dataset (harmful-behavior prompts, even though HarmBench itself is MIT).
- `reshabhs/SPML_Chatbot_Prompt_Injection` (card says MIT, but the system prompts start from leaked chatbot prompts and the authors say not to train a detector on it).
- `quickium/prompt-security-v0` as a compilation, because the permissive split also mixes GPL-3.0 and ODC-BY, and the other split is CC BY-NC.
- Meta Prompt Guard (Llama license).

### Original text

- Source field: `myxguard-train-original`
- License: MIT, copyright XYMYX, same terms as `LICENSE`
- What it is: template-built and hand-written attacks and benign hard negatives in English, German, French, Italian, and Swiss German (everyday chat, email, support, recipes, code, code comments, logs, base64 images, security notes that quote an injection, and “ignore the previous email”), including filler words, dialect spellings, mixed languages, and hidden markup.

### Tatoeba

- Source: https://tatoeba.org
- License: CC BY 2.0 FR (the API field on each included sentence)
- What we used: everyday sentences in English, German, French, Italian, and Swiss German that are not near-duplicates of the held-out or dev sets
- Attribution: `source` is `tatoeba.org:<sentence id>:<username>`. Copyright stays with those contributors. Terms: https://tatoeba.org/en/terms_of_use
- Fetch: `https://api.tatoeba.org/unstable/sentences` with `sort=random:20261026`

### deepset/prompt-injections

- Same project as the sample and the held-out rows above
- License on the Hub tag and the card front matter: `apache-2.0` (checked 2026-10-26). The card's `dataset_info.license` field also says `cc-by-4.0`. Both are allowed. Rows in this corpus are marked Apache-2.0, matching the Hub tag and the earlier notice.
- What we used: further train and test rows that are clearly injections or ordinary questions, in English and German. Rows already too close to held-out or dev text were dropped. Political, hateful, and ordinary tasks that deepset marks positive but that are not injection attempts were left out.

### neuralchemy/Prompt-injection-dataset

- Source: https://huggingface.co/datasets/neuralchemy/Prompt-injection-dataset
- License: Apache-2.0 on the dataset card (checked 2026-10-26)
- What we used: a capped sample of rows whose own `source` is `original` or `neuralchemy_v1` (the card's NeurAlchemy material). Unsafe and political rows were skipped.
- What we did not copy: `wildguard_judgecomp`, `harmbench`, `harmbench_benign`.

### hackaprompt/hackaprompt-dataset

- Same MIT dataset as the held-out notice above (official card `license: mit`, checked 2026-10-26). NeurAlchemy's table says CC BY 4.0 for this slice. This tree follows the official MIT card.
- What we used: a small capped sample of competition prompts that NeurAlchemy redistributes with `source` `hackaprompt`. The official Hugging Face file is gated and was not downloaded. Long and unsafe submissions were not selected.
- The MIT notice for HackAPrompt contributors is printed in the held-out section above.

### 3nesdeniz/english-prompt-injection-3k

- Source: https://huggingface.co/datasets/3nesdeniz/english-prompt-injection-3k
- License: CC-BY-4.0 (card front matter `license: cc-by-4.0`, checked 2026-10-26)
- Author: Enes Deniz
- What we used: a capped sample of the train split only (benign hard negatives and attack families). The validation and test splits were not copied.
- Attribution: "English Prompt-Injection 3K" by Enes Deniz, CC BY 4.0, https://huggingface.co/datasets/3nesdeniz/english-prompt-injection-3k

### Shomi28/prompt-injection-dataset

- Source: https://huggingface.co/datasets/Shomi28/prompt-injection-dataset
- License: MIT (card front matter, checked 2026-10-26)
- Author: Soham Dahivalkar, 2026
- What we used: a capped sample of the train split. The card describes the rows as the author's labeled prompts, including synthetic variations.

The MIT license requires this notice:

```
MIT License

Copyright (c) 2026 Soham Dahivalkar

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
Lakera/gandalf_ignore_instructions
Source: https://huggingface.co/datasets/Lakera/gandalf_ignore_instructions (revision 04737b65e90a6794ec227012e4a255a7def6344b)
License: MIT (dataset card)
Copyright: Lakera AI. The card does not print a separate copyright line. Cite Pfister et al., "Gandalf the Red: Adaptive Security for LLMs", arXiv:2501.07927, 2025.
What we used: English prompts submitted to the Gandalf game, only in the fresh test set datasets/test_fresh/. Not used for training, dev or rule tuning. Raw copy in datasets/test_fresh/raw/.
MIT License

Copyright (c) Lakera AI

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## Optional classifier

`protectai/deberta-v3-base-prompt-injection-v2` is the default ONNX model behind `scan(..., config=ScanConfig(ml=True))` and `myxguard check --ml`.

Checked on 2026-10-26:

- Model card front matter: `license: apache-2.0`.
- Model card body: "License: Apache License 2.0".
- Hugging Face API tag: `license:apache-2.0`.
- Repository file `LICENSE` is present. The Apache-2.0 text used by this package is `LICENSES/Apache-2.0.txt`.
- Base model named on the card: `microsoft/deberta-v3-base`.
- `onnx/config.json` labels: `0 = SAFE`, `1 = INJECTION`.
- The card says the model is for English prompt injection and does not handle non-English prompts or jailbreaks well.

Source: https://huggingface.co/protectai/deberta-v3-base-prompt-injection-v2

MyxGuard downloads `onnx/model.onnx`, `onnx/tokenizer.json`, and `onnx/config.json` on first use. The weights are not committed in this repository. Fine-tuned by Protect AI. The project is marked archived on the model card.

A later fine-tune may use `xlm-roberta-base` (MIT on the Hugging Face model card) or `microsoft/mdeberta-v3-base` (MIT on the Hugging Face model card). See `training/README.md`.

## Not used

- https://github.com/tldrsec/prompt-injection-defenses — no license file. Nothing was copied.
- Lakera PINT — not used.
- Meta Prompt Guard (Llama license) — not used. The optional classifier is the Apache-2.0 Protect AI model above.
