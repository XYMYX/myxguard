# Held-out eval set

`heldout.jsonl` is for measuring MyxGuard. It was not used to write or tune the rules in `myxguard/data/patterns/`.

Do not add or delete rows to make the score look better. If a rule changes, record the before and after numbers from:

```bash
python scripts/benchmark.py datasets/eval/heldout.jsonl --eval
```

The regression file `datasets/samples.jsonl` is separate. A perfect score there only means the rules still match the examples they were written with.

Each line has `text`, `label` (`malicious` or `benign`), `language`, `category`, `source`, and `license`. A `note` field, when present, explains an encoded payload for a human reader. The scanner does not read `note`.

Sources and licenses are listed in `THIRD_PARTY_NOTICES.md`.
