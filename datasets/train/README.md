# Training corpus

`train.jsonl` is the default input of `training/finetune.py`.
Each row has `text`, `label` (`malicious` or `benign`), `language`, `category`, `source`, and `license`.

Nothing in this file is copied from `datasets/eval/heldout.jsonl`.
The build also drops near-duplicates of that file and of `datasets/dev/dev.jsonl`.
Dev stays the validation split and is not mixed into these rows.

Rebuild (needs network for Tatoeba, and for Hugging Face if the cache is empty):

```bash
python training/build_corpus.py
python scripts/dataset_stats.py datasets/train/train.jsonl
```

Rows in this build: 2576.

Before the per-language cap, the builder dropped 48 exact overlaps, 3 contained overlaps, and 2 high-similarity overlaps with the held-out file or the dev set, plus 17 internal exact duplicates. The file that remains has no near-duplicate of either split. Upstream skips (not copied): 341 research-only or HarmBench rows, 282 deepset rows that are not injection attempts, 34 political or hateful rows, 22 unsafe rows.

## Label

| key | rows |
| --- | ---: |
| benign | 1300 |
| malicious | 1276 |

## Language

| key | rows |
| --- | ---: |
| de | 520 |
| en | 520 |
| fr | 511 |
| gsw | 512 |
| it | 513 |

## Category

| key | rows |
| --- | ---: |
| base64_image | 90 |
| code | 64 |
| code_comment | 64 |
| data_exfiltration | 190 |
| delimiter_injection | 114 |
| email | 117 |
| everyday | 207 |
| hard_negative | 95 |
| hidden_html | 39 |
| hidden_unicode | 24 |
| ignore_previous_email | 117 |
| indirect_injection | 152 |
| instruction_override | 261 |
| jailbreak_persona | 188 |
| log | 128 |
| mixed_chat | 68 |
| mixed_language | 68 |
| obfuscation | 104 |
| recipe | 116 |
| role_impersonation | 68 |
| security_discussion | 117 |
| support | 117 |
| tool_abuse | 68 |

## Source

| key | rows |
| --- | ---: |
| 3nesdeniz/english-prompt-injection-3k | 154 |
| Shomi28/prompt-injection-dataset | 35 |
| deepset/prompt-injections | 93 |
| hackaprompt/hackaprompt-dataset | 10 |
| myxguard-train-original | 2073 |
| neuralchemy/Prompt-injection-dataset | 118 |
| tatoeba.org | 93 |

## License

| key | rows |
| --- | ---: |
| Apache-2.0 | 211 |
| CC-BY-2.0-FR | 93 |
| CC-BY-4.0 | 154 |
| MIT | 2118 |

Sources and the license check are recorded in `THIRD_PARTY_NOTICES.md`.
Original rows use source `myxguard-train-original` and the MIT license of this package.
