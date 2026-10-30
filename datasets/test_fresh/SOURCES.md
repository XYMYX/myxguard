# Sources of datasets/test_fresh

| Source | Rows downloaded | License | Languages | Used for |
|---|---:|---|---|---|
| `Lakera/gandalf_ignore_instructions` | 1000 | MIT | en | English attacks (sample drawn in S5) |
| `myxguard-fresh-handwritten` | 720 written, 559 kept | MIT (this repo) | de, fr, it, en | attacks and benign texts in all four languages |

## Lakera/gandalf_ignore_instructions

- URL: https://huggingface.co/datasets/Lakera/gandalf_ignore_instructions
- Revision: `04737b65e90a6794ec227012e4a255a7def6344b` (last modified 2025-02-28), not gated
- Downloaded: 2026-10-30 with `scripts/fetch_gandalf.py` (Hugging Face rows API, JSON). Revision was checked before and after the download and did not change.
- Raw file, unchanged upstream rows plus `split`: `raw/gandalf_ignore_instructions.jsonl` (fields `text`, `similarity`, `split`). Metadata: `raw/gandalf_ignore_instructions.meta.json`.
- License: MIT, from the dataset card (`license: mit`). The card prints no separate copyright line, so the holder is recorded as Lakera AI.
- Citation requested by the card: Pfister et al., "Gandalf the Red: Adaptive Security for LLMs", arXiv:2501.07927, 2025.
- From the card: the prompts were submitted to the Gandalf game in July 2023 and filtered by embedding similarity (≥ 0.825) to "Ignore all previous instructions". PII was filtered and near-duplicates removed. The card warns that a few rows may not be real prompt injections.
- Status in this repo: not used in `datasets/train`, `datasets/dev` or `datasets/eval`. `git grep -i gandalf -- datasets/train datasets/dev datasets/eval training THIRD_PARTY_NOTICES.md` finds nothing (2026-10-30). Lakera appears only in `THIRD_PARTY_NOTICES.md` as "Lakera PINT — not used", which is a different dataset.

### Leakage pre-check on the raw pool (2026-10-30)

`python scripts/check_leakage.py datasets/test_fresh/raw/gandalf_ignore_instructions.jsonl`, 1000 rows checked against 3326 blocked texts:

| Against | Hits |
|---|---:|
| train / dev / eval / samples / deepset_sample / old fresh set | 0 |
| other Gandalf rows (near-duplicates inside the pool) | 89 (78 ratio, 10 jaccard, 1 exact after normalizing) |
| cannot be checked (normalizes to empty text, non-Latin only) | 1 |

These 90 rows are excluded from the pool before sampling. The real check (S6) runs again on the built `test_fresh.jsonl`.

### Limits

- English only. The attack style is narrow: almost every row is a variant of "ignore your instructions" or "tell me your instructions/password", because the upstream filter picked rows close to one phrase.
- Category for all Gandalf rows: `instruction_override` (decided 2026-10-30, before any detector run). Many rows also try to extract the secret, so the category is coarse.
- Sample: 50 rows, `random.Random(20261030)`, drawn from the 910 rows left after the leakage pre-check. Drawn without looking at detector scores.
- Label noise per the card: a few rows may not be injections. They are not filtered by hand, because that would mean picking rows by eye.

## Hand-written rows

Source `myxguard-fresh-handwritten`, license MIT. Written by the project owner (confirmed for `fresh_raw2.txt` on 2026-10-30), not by a model.

| File | sha256 | Rows | Kept | Removed by leakage check |
|---|---|---:|---:|---:|
| `raw/fresh_raw1.txt` | `e6070ede71c7595c…` | 360 | 199 | 161 (160 exact copies of the old fresh set `../apertus/test_fresh.jsonl`, 1 near-duplicate of a `train.jsonl` row) |
| `raw/fresh_raw2.txt` | `a2c79a3ef7520b46…` | 360 | 360 | 0 |

Removed rows with reasons: `removed_by_leakage.jsonl`. Known limit, from the author: many role-play attacks in `fresh_raw2.txt` share one underlying idea across all four languages, written separately in each language. That makes the language comparison fairer but the set less varied.
