#!/usr/bin/env python3
"""Fine-tune a small multilingual classifier and export it to ONNX.

This script is preparation for a later training run. It is not executed by
tests or by the MyxGuard scanner. PyTorch and Transformers are imported only
after the arguments are checked, and they are listed in
``training/requirements.txt``, not in the runtime extra ``myxguard[ml]``.

Default base model: ``xlm-roberta-base`` (MIT, model card on Hugging Face).
``microsoft/mdeberta-v3-base`` is also MIT and is a drop-in alternative via
``--base-model``. Do not use Meta Prompt Guard. Its license is the Llama
license, which this project does not accept.

The export writes ``model.onnx``, ``tokenizer.json``, and ``config.json``
with labels SAFE=0 and INJECTION=1, which is what ``MYXGUARD_MODEL_PATH``
expects.

The default training file is ``datasets/train/train.jsonl``. The dev set is
the validation split and is not mixed into training. Held-out text, including
near-duplicates, is removed.

Example (from the repository root, after installing the training requirements)::

    python training/finetune.py \\
        --train datasets/train/train.jsonl \\
        --validation datasets/dev/dev.jsonl \\
        --exclude datasets/eval/heldout.jsonl \\
        --output training/output/myxguard-xlm-roberta

``--smoke`` runs one tiny randomly initialised model on a handful of rows so
the ONNX export can be checked on CPU. That export is not a real detector.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from training.data import prepare

_DEFAULT_BASE = "xlm-roberta-base"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fine-tune and export an ONNX classifier.")
    parser.add_argument(
        "--train",
        nargs="+",
        default=[str(_ROOT / "datasets" / "train" / "train.jsonl")],
        help="JSONL files with text and label. Do not pass datasets/eval/heldout.jsonl.",
    )
    parser.add_argument(
        "--validation",
        default=str(_ROOT / "datasets" / "dev" / "dev.jsonl"),
        help="JSONL used only for validation. Default: the dev set.",
    )
    parser.add_argument(
        "--exclude",
        default=str(_ROOT / "datasets" / "eval" / "heldout.jsonl"),
        help="JSONL whose texts are removed from training (default: the held-out eval set).",
    )
    parser.add_argument(
        "--output",
        default=str(_ROOT / "training" / "output" / "myxguard-xlm-roberta"),
        help="Folder for the ONNX export.",
    )
    parser.add_argument("--base-model", default=_DEFAULT_BASE)
    parser.add_argument("--epochs", type=int, default=2)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--max-length", type=int, default=256)
    parser.add_argument("--learning-rate", type=float, default=2e-5)
    parser.add_argument(
        "--augment",
        action="store_true",
        help="Add a few extra original lines. The train corpus already covers those languages.",
    )
    parser.add_argument(
        "--no-augment",
        action="store_true",
        help="Accepted for older commands. Extra lines stay off unless --augment is set.",
    )
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Train a tiny random model on a few rows and export ONNX. Not a real detector.",
    )
    args = parser.parse_args(argv)
    if args.smoke:
        args.epochs = 1
        args.batch_size = 2
        args.max_length = 32
        args.output = args.output if args.output else str(_ROOT / "training" / "output" / "smoke")
    train_paths = [Path(item) for item in args.train]
    exclude = Path(args.exclude) if args.exclude else None
    validation = Path(args.validation) if args.validation else None
    block_paths = []
    if validation is not None and validation.is_file():
        block_paths.append(validation)
    try:
        for path in train_paths:
            if validation is not None and path.resolve() == validation.resolve():
                raise ValueError(
                    f"Refusing to train on {path}. The dev set is the validation split."
                )
        rows = prepare(
            train_paths,
            exclude=exclude,
            block_paths=block_paths,
            augment=args.augment and not args.no_augment,
        )
        val_rows = _load_validation(validation)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if args.smoke:
        rows = _balanced_subset(rows, 8)
        val_rows = _balanced_subset(val_rows, 4) or rows[:2]
    try:
        _train_and_export(rows, val_rows, args)
    except ImportError:
        print(
            "Training dependencies are missing. On a GPU machine or Colab, run:\n"
            "  pip install -r training/requirements.txt\n"
            "Those packages are not part of myxguard or myxguard[ml].",
            file=sys.stderr,
        )
        return 2
    return 0


def _load_validation(path: Path | None) -> list[dict[str, str]]:
    if path is None or not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        if record.get("label") in {"malicious", "benign"} and isinstance(record.get("text"), str):
            rows.append({"text": record["text"], "label": record["label"]})
    return rows


def _balanced_subset(rows: list[dict[str, str]], count: int) -> list[dict[str, str]]:
    malicious = [row for row in rows if row["label"] == "malicious"]
    benign = [row for row in rows if row["label"] == "benign"]
    half = max(1, count // 2)
    picked = malicious[:half] + benign[:half]
    return picked[:count] or rows[:count]


def _train_and_export(
    rows: list[dict[str, str]],
    val_rows: list[dict[str, str]],
    args: argparse.Namespace,
) -> None:
    import torch
    from transformers import (
        AutoModelForSequenceClassification,
        AutoTokenizer,
        Trainer,
        TrainingArguments,
    )

    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    if args.smoke:
        tokenizer = _smoke_tokenizer()
        model = _smoke_model()
    else:
        tokenizer = AutoTokenizer.from_pretrained(args.base_model)
        model = AutoModelForSequenceClassification.from_pretrained(
            args.base_model,
            num_labels=2,
            id2label={0: "SAFE", 1: "INJECTION"},
            label2id={"SAFE": 0, "INJECTION": 1},
        )
    encoded = _encode(rows, tokenizer, args.max_length)
    if val_rows:
        eval_encoded = _encode(val_rows, tokenizer, args.max_length)
    else:
        split_at = max(1, int(len(encoded) * 0.9))
        if split_at >= len(encoded):
            split_at = len(encoded) - 1
        eval_encoded = encoded[split_at:] or encoded[:1]
        encoded = encoded[:split_at]
    train_set = _TensorRows(encoded)
    eval_set = _TensorRows(eval_encoded)
    use_cuda = torch.cuda.is_available()
    training_args = TrainingArguments(
        output_dir=str(output / "checkpoints"),
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        eval_strategy="epoch",
        save_strategy="no",
        logging_steps=20,
        report_to=[],
        fp16=use_cuda,
        dataloader_pin_memory=use_cuda,
    )
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_set,
        eval_dataset=eval_set,
    )
    trainer.train()
    _export_onnx(model, tokenizer, output, args.max_length)


def _smoke_tokenizer():
    """Whitespace tokenizer used only by --smoke. It is not a trained model."""
    from tokenizers import Tokenizer
    from tokenizers.models import WordLevel
    from tokenizers.pre_tokenizers import Whitespace
    from transformers import PreTrainedTokenizerFast

    pieces: list[str] = []
    for piece in (
        "<pad>",
        "<unk>",
        "<s>",
        "</s>",
        "ignore",
        "previous",
        "instructions",
        "please",
        "hello",
        "the",
        "and",
        "to",
        "of",
        *list("abcdefghijklmnopqrstuvwxyz"),
    ):
        if piece not in pieces:
            pieces.append(piece)
    vocab = {piece: index for index, piece in enumerate(pieces)}
    raw = Tokenizer(WordLevel(vocab, unk_token="<unk>"))
    raw.pre_tokenizer = Whitespace()
    tokenizer = PreTrainedTokenizerFast(
        tokenizer_object=raw,
        unk_token="<unk>",
        pad_token="<pad>",
        bos_token="<s>",
        eos_token="</s>",
    )
    tokenizer.model_max_length = 64
    return tokenizer


def _smoke_model():
    """One-layer random classifier. Exists so CPU can check the export path."""
    from transformers import XLMRobertaConfig, XLMRobertaForSequenceClassification

    config = XLMRobertaConfig(
        vocab_size=48,
        hidden_size=32,
        num_hidden_layers=1,
        num_attention_heads=4,
        intermediate_size=64,
        max_position_embeddings=64,
        type_vocab_size=1,
        pad_token_id=0,
        bos_token_id=2,
        eos_token_id=3,
        num_labels=2,
        id2label={0: "SAFE", 1: "INJECTION"},
        label2id={"SAFE": 0, "INJECTION": 1},
    )
    return XLMRobertaForSequenceClassification(config)


def _encode(rows: list[dict[str, str]], tokenizer: object, max_length: int) -> list[dict]:
    import torch

    encoded_rows = []
    for row in rows:
        encoded = tokenizer(
            row["text"],
            truncation=True,
            max_length=max_length,
            padding="max_length",
        )
        item = {
            "input_ids": torch.tensor(encoded["input_ids"]),
            "attention_mask": torch.tensor(encoded["attention_mask"]),
            "labels": torch.tensor(1 if row["label"] == "malicious" else 0),
        }
        encoded_rows.append(item)
    return encoded_rows


class _TensorRows:
    """Small dataset object the Transformers Trainer can index."""

    def __init__(self, items: list[dict]) -> None:
        self.items = items

    def __len__(self) -> int:
        return len(self.items)

    def __getitem__(self, index: int) -> dict:
        return self.items[index]


def _export_onnx(model: object, tokenizer: object, output: Path, max_length: int) -> None:
    import torch

    class _Logits(torch.nn.Module):
        def __init__(self, inner: torch.nn.Module) -> None:
            super().__init__()
            self.inner = inner

        def forward(self, input_ids: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor:
            return self.inner(input_ids=input_ids, attention_mask=attention_mask).logits

    wrapped = _Logits(model)
    wrapped.eval()
    dummy = tokenizer("hello", return_tensors="pt", truncation=True, max_length=max_length)
    onnx_path = output / "model.onnx"
    torch.onnx.export(
        wrapped,
        (dummy["input_ids"], dummy["attention_mask"]),
        str(onnx_path),
        input_names=["input_ids", "attention_mask"],
        output_names=["logits"],
        dynamic_axes={
            "input_ids": {0: "batch", 1: "sequence"},
            "attention_mask": {0: "batch", 1: "sequence"},
            "logits": {0: "batch"},
        },
        opset_version=17,
        dynamo=False,
        external_data=False,
    )
    tokenizer.save_pretrained(output)
    config = {
        "id2label": {"0": "SAFE", "1": "INJECTION"},
        "label2id": {"SAFE": 0, "INJECTION": 1},
        "model_type": "myxguard-sequence-classification",
    }
    (output / "config.json").write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    print(f"Exported ONNX model to {output}")
    print("Point the scanner at it with:")
    print(f"  MYXGUARD_MODEL_PATH={output} python -m myxguard check examples/ignore.txt --ml")


if __name__ == "__main__":
    raise SystemExit(main())
