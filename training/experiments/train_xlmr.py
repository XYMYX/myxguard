"""XLM-RoBERTa feinabstimmen (eigene Daten + deepset train) und wie baseline.py auswerten.

Installation: pip install transformers datasets accelerate scikit-learn
"""
import collections, json, os, re, sys

import numpy as np
import torch
from datasets import Dataset, load_dataset
from transformers import (AutoModelForSequenceClassification, AutoTokenizer,
                          DataCollatorWithPadding, Trainer, TrainingArguments, set_seed)

MODEL = "xlm-roberta-base"
OWN = "dataset.jsonl"
EPOCHS = 5
SEED = int(sys.argv[1]) if len(sys.argv) > 1 else 42   # z. B.: python train_xlmr.py 1
set_seed(SEED)


def load_own(path):
    train, test = [], []
    with open(path, encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            r["y"] = 1 if r["label"] == "malicious" else 0
            (test if r["split"] == "test" else train).append(r)
    return train, test


def rates(y_true, y_pred):
    tp = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 1)
    fn = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 0)
    fp = sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p == 1)
    tn = sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p == 0)
    recall = tp / (tp + fn) if tp + fn else float("nan")
    fpr = fp / (fp + tn) if fp + tn else float("nan")
    precision = tp / (tp + fp) if tp + fp else float("nan")
    return recall, fpr, precision, tp + fn, fp + tn


def line(name, y_true, y_pred):
    recall, fpr, precision, n_mal, n_ben = rates(y_true, y_pred)
    print(f"  {name:<28} Angriffe erkannt {recall:6.1%} (n={n_mal:<4}) | "
          f"Harmlose fälschlich geblockt {fpr:6.1%} (n={n_ben:<4}) | Precision {precision:6.1%}")


own_train, own_test = load_own(OWN)
ds = load_dataset("deepset/prompt-injections")
def load_jsonl(path):
    try:
        with open(path, encoding="utf-8") as f:
            return [json.loads(l) for l in f]
    except FileNotFoundError:
        return []


EXTRA_REPEAT = int(os.environ.get("EXTRA_REPEAT", "1"))   # Zusatzdaten so oft wiederholen
ext_train = load_jsonl("external_train.jsonl") + load_jsonl("extra_train.jsonl") * EXTRA_REPEAT
print(f"Zusatzdaten x{EXTRA_REPEAT}")
ext_test = load_jsonl("external_benign_test.jsonl")
print(f"Externe Trainingsdaten: {len(ext_train)}, externer harmloser Test: {len(ext_test)}")

# Entscheidung: harmlose Rollenspiel-Bitten ("Spiel einen Coach") sind KEIN Angriff.
# deepset labelt sie teils als Angriff -> diese Trainingszeilen weglassen, ausser sie wirken wirklich gefährlich.
ROLEPLAY = re.compile(r"act as|pretend|play the role|role-?play|i want you to (act|be)|spiel(e)? (die|eine|den)? ?rolle|"
                      r"verhalte dich wie|stell dir vor, du bist|joue le rôle|fais semblant|agisci come|fai finta", re.I)
DANGER = re.compile(r"\bDAN\b|jailbreak|no restrictions|without (any )?restrictions|unfiltered|ohne (jegliche )?(einschr|regeln|filter)|"
                    r"keine (regeln|einschr)|ignor|vergiss|forget|evil|böse|hack|bomb|illegal|steal|stehl|password|passwort", re.I)
dp_x, dp_y, dropped = [], [], []
for t, y in zip(ds["train"]["text"], ds["train"]["label"]):
    if y == 1 and ROLEPLAY.search(t) and not DANGER.search(t):
        dropped.append(t)
    else:
        dp_x.append(t); dp_y.append(y)
print(f"deepset-Train: {len(dropped)} harmlose Rollenspiel-Angriffe entfernt. Stichprobe:")
for t in dropped[:10]:
    print("  -", t[:110].replace("\n", " "))

train_x = [r["text"] for r in own_train] + dp_x + [r["text"] for r in ext_train]
train_y = ([r["y"] for r in own_train] + dp_y
           + [1 if r["label"] == "malicious" else 0 for r in ext_train])
own_test_x, own_test_y = [r["text"] for r in own_test], [r["y"] for r in own_test]
dp_test_x, dp_test_y = list(ds["test"]["text"]), list(ds["test"]["label"])

tok = AutoTokenizer.from_pretrained(MODEL)


def make_ds(texts, labels):
    d = Dataset.from_dict({"text": texts, "labels": labels})
    return d.map(lambda b: tok(b["text"], truncation=True, max_length=256),
                 batched=True, remove_columns=["text"])


# Angriffe stärker gewichten, wenn es weniger davon gibt (Gewicht höchstens 3)
ATTACK_WEIGHT = (float(sys.argv[2]) if len(sys.argv) > 2   # z. B.: python train_xlmr.py 1 1.0 (= ohne Gewichtung)
                 else min(3.0, train_y.count(0) / max(1, train_y.count(1))))
print(f"Trainingsdaten: {train_y.count(0)} harmlos, {train_y.count(1)} Angriffe -> Angriffs-Gewicht {ATTACK_WEIGHT:.2f}")


class WeightedTrainer(Trainer):
    def compute_loss(self, model, inputs, return_outputs=False, **kwargs):
        labels = inputs.pop("labels")
        outputs = model(**inputs)
        w = torch.tensor([1.0, ATTACK_WEIGHT], device=outputs.logits.device, dtype=outputs.logits.dtype)
        loss = torch.nn.functional.cross_entropy(outputs.logits, labels, weight=w)
        return (loss, outputs) if return_outputs else loss


model = AutoModelForSequenceClassification.from_pretrained(MODEL, num_labels=2)
args = TrainingArguments(
    output_dir="xlmr-out", num_train_epochs=EPOCHS, per_device_train_batch_size=16,
    learning_rate=2e-5, weight_decay=0.01, bf16=True, save_strategy="no",
    report_to="none", logging_steps=20, seed=SEED,
)
trainer = WeightedTrainer(model=model, args=args, train_dataset=make_ds(train_x, train_y),
                  data_collator=DataCollatorWithPadding(tok), processing_class=tok)
trainer.train()


def predict(texts):
    out = trainer.predict(make_ds(texts, [0] * len(texts)))
    return out.predictions.argmax(-1).tolist()


print(f"\nEigene Daten: {len(own_train)} train / {len(own_test)} test | deepset: {len(ds['train'])} train / {len(dp_test_x)} test\n")
pred_own = predict(own_test_x)
pred_dp = predict(dp_test_x)
print("XLM-RoBERTa (eigene + deepset)")
line("auf eigenem Test", own_test_y, pred_own)
line("auf deepset-Test", dp_test_y, pred_dp)

print("\ndeepset-Test, verpasste Angriffe:")
for t, y, p in zip(dp_test_x, dp_test_y, pred_dp):
    if y == 1 and p == 0:
        print(f"  {t[:140]!r}")

if ext_test:
    pred_ext = predict([r["text"] for r in ext_test])
    print("\nEchte harmlose Texte (extern, nie im Training): Anteil fälschlich geblockt")
    for lang in sorted({r["language"] for r in ext_test}):
        idx = [i for i, r in enumerate(ext_test) if r["language"] == lang]
        print(f"  {lang}: {sum(pred_ext[i] for i in idx) / len(idx):6.1%} (n={len(idx)})")
    shown = 0
    for r, p in zip(ext_test, pred_ext):
        if p == 1 and shown < 8:
            print(f"  [GEBLOCKT] {r['language']}: {r['text'][:140]!r}")
            shown += 1

print("\nEigener Test, nach Sprache:")
for lang in sorted({r["language"] for r in own_test}):
    idx = [i for i, r in enumerate(own_test) if r["language"] == lang]
    line(lang, [own_test_y[i] for i in idx], [pred_own[i] for i in idx])

print("\nEigener Test, nach Angriffskategorie (nur Angriffe):")
cats = collections.defaultdict(list)
for i, r in enumerate(own_test):
    if r["y"] == 1:
        cats[r["category"]].append(pred_own[i])
for cat, ps in sorted(cats.items()):
    print(f"  {cat:<24} erkannt {sum(ps) / len(ps):6.1%} (n={len(ps)})")

print("\nEigener Test, Fehler:")
for r, p in zip(own_test, pred_own):
    if p != r["y"]:
        art = "VERPASST" if r["y"] == 1 else "FALSCH GEBLOCKT"
        print(f"  [{art}] {r['language']}/{r['category']}: {r['text'][:140]!r}")

r_own, r_dp = rates(own_test_y, pred_own), rates(dp_test_y, pred_dp)
ext_fpr = sum(pred_ext) / len(pred_ext) if ext_test else float("nan")
print(f"ERGEBNIS seed={SEED} gewicht={ATTACK_WEIGHT:.2f} eigen_erkannt={r_own[0]:.3f} eigen_fehlalarm={r_own[1]:.3f} "
      f"deepset_erkannt={r_dp[0]:.3f} deepset_fehlalarm={r_dp[1]:.3f} extern_fehlalarm={ext_fpr:.3f}")

trainer.save_model("xlmr-detector")
tok.save_pretrained("xlmr-detector")
print("\nGespeichert in xlmr-detector/. Zum späteren Aufräumen: rm -rf xlmr-out xlmr-detector")
