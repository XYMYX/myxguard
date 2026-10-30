# Fresh test set

Measures MyxGuard on wording it has never seen. Not for training, not for tuning rules or thresholds. Evaluated once, at the end.

## Hand-written rows

One file per language: `handwritten_de.jsonl`, `handwritten_fr.jsonl`, `handwritten_it.jsonl`, `handwritten_en.jsonl`. One JSON object per line:

```json
{"text": "…", "label": "malicious", "language": "de", "category": "data_exfiltration", "source": "myxguard-fresh-handwritten", "license": "MIT"}
{"text": "…", "label": "benign", "language": "de", "category": "benign", "source": "myxguard-fresh-handwritten", "license": "MIT", "note": "roleplay"}
```

| Field | Values |
|---|---|
| `label` | `malicious` or `benign` |
| `category` | `instruction_override`, `data_exfiltration`, `jailbreak_persona` (all `malicious`) or `benign` |
| `note` | required on benign rows: `plain` (ordinary text), `roleplay` (harmless role-play request, e.g. "play a strict coach"), `hard_negative` (harmless but sounds suspicious, e.g. quotes an attack or says "ignore the footnotes") |
| `language` | the file's language |

Target per language: at least 15 rows for each attack category, and at least 45 benign rows (at least 15 `roleplay`, at least 15 `hard_negative`). Fewer is allowed; the report states the real counts.

Rules for writing:

- Write the text yourself or have people write it, native speakers for fr/it/de if possible. No model generation (no Apertus, no Claude).
- Do not copy or rephrase rows from `datasets/train`, `datasets/dev`, `datasets/eval` or the old fresh set. The leakage check removes near-duplicates before scoring, and each removal is counted.
- Use new attack ideas, not just new words for the old ones.
- Do not run the detector on your rows while writing them.

## Checks

```bash
python scripts/check_schema.py
python scripts/check_leakage.py
```

Sources and licenses of external rows: `SOURCES.md` (created in S3, after the download is approved).
