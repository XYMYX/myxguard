# Dev set

`dev.jsonl` is original text written for MyxGuard (MIT, XYMYX, source `myxguard-dev-original`). It uses the same languages and category names as the held-out eval set. It is the set you may change when you adjust a rule.

Do not copy rows from `datasets/eval/heldout.jsonl`, and do not edit that file to chase a score. Measure the held-out file only after the rule change is finished:

```bash
python scripts/benchmark.py datasets/dev/dev.jsonl --eval
python scripts/benchmark.py datasets/samples.jsonl
python scripts/benchmark.py datasets/eval/heldout.jsonl --eval
```

A row counts as detected when the score is at least 25. A verb and a noun with no "earlier" word stay under that line on purpose.
