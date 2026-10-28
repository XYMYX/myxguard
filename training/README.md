# Fine-tune a multilingual MyxGuard classifier

This folder trains a later replacement for the English Protect AI model. Nothing here runs during `pytest` or during a normal scan. The scanner stays rules-only unless you pass `--ml`.

## Data

Default training file: `datasets/train/train.jsonl` (about 2,600 rows).

Default validation file: `datasets/dev/dev.jsonl`. It is not mixed into training.

`datasets/eval/heldout.jsonl` is refused as a path. Exact copies and near-duplicates of that file, and of the dev set, are removed before the first step. Rebuild the corpus with `python training/build_corpus.py` (network for Tatoeba, and for Hugging Face if `training/.cache` is empty). Counts: `python scripts/dataset_stats.py datasets/train/train.jsonl`.

Row licenses are only MIT, Apache-2.0, CC-BY-4.0, or CC BY 2.0 FR. The source list is in `THIRD_PARTY_NOTICES.md`.

## Models

| Model | Card | Use |
| --- | --- | --- |
| `xlm-roberta-base` | MIT | Default base model. German, French, and Italian are in its language list. |
| `microsoft/mdeberta-v3-base` | MIT | Alternative: `--base-model microsoft/mdeberta-v3-base` |
| `protectai/deberta-v3-base-prompt-injection-v2` | Apache-2.0 | The optional runtime model already wired up. English only. |
| Meta Prompt Guard | Llama license | Do not use. |

## What the script does

1. Load `datasets/train/train.jsonl` (or the files you pass to `--train`).
2. Drop held-out text and dev text, including near-duplicates.
3. Fine-tune with labels `SAFE=0` and `INJECTION=1`. Dev is the eval split.
4. Export `model.onnx`, `tokenizer.json`, and `config.json`.

`--smoke` runs the same steps on CPU with a tiny random model and a handful of rows. That export is only a pipeline check. Do not point the scanner at it for real traffic.

Plug a real export in without changing code:

```bash
export MYXGUARD_MODEL_PATH=training/output/myxguard-xlm-roberta
python -m myxguard check examples/ignore.txt --ml
```

`--ml-model` on the CLI and `ml_model_path` on the MCP `scan_text` tool do the same. The scan machine needs `pip install "myxguard[ml]"` (onnxruntime and tokenizers). It does not need PyTorch.

## Google Colab (free T4 GPU)

These are the steps for the real training run. A free T4 session is enough for this corpus (about 2,600 rows, two epochs).

1. Upload this repository, or clone it, so the notebook can see `datasets/train/train.jsonl`, `datasets/dev/dev.jsonl`, and `datasets/eval/heldout.jsonl`.
2. Menu: Runtime → Change runtime type → T4 GPU.
3. Run:

```bash
pip install -r training/requirements.txt
python training/finetune.py \
  --train datasets/train/train.jsonl \
  --validation datasets/dev/dev.jsonl \
  --exclude datasets/eval/heldout.jsonl \
  --base-model xlm-roberta-base \
  --epochs 2 \
  --batch-size 8 \
  --max-length 256 \
  --learning-rate 2e-5 \
  --output training/output/myxguard-xlm-roberta
```

Those flags match the script defaults, so `python training/finetune.py` is the same command. Download the folder `training/output/myxguard-xlm-roberta` and set `MYXGUARD_MODEL_PATH` to it.

`xlm-roberta-base` is about 270 million parameters. If the GPU runs out of memory, rerun with `--batch-size 4 --max-length 128`.

To use the other MIT base instead, add `--base-model microsoft/mdeberta-v3-base` and change the output folder name. Do not train on `datasets/eval/heldout.jsonl`.
