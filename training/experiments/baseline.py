"""Baseline: TF-IDF (Zeichen-N-Gramme) + logistische Regression.

Trainiert drei Varianten und wertet jede auf zwei getrennten Test-Sets aus:
  A = nur eigene Daten (split == train)
  B = nur deepset/prompt-injections (train)
  C = beides zusammen
Test-Sets:
  eigener Test (split == test, Vorlagen die im Training nie vorkamen)
  deepset-Test (von Menschen geschrieben, nie im Training)

Installation: pip install scikit-learn datasets
"""
import collections, json

import numpy as np

from datasets import load_dataset
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline

OWN = "dataset.jsonl"


def load_own(path):
    train, test = [], []
    with open(path, encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            r["y"] = 1 if r["label"] == "malicious" else 0
            (test if r["split"] == "test" else train).append(r)
    return train, test


def fit(texts, labels):
    model = make_pipeline(
        TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), sublinear_tf=True, min_df=2),
        LogisticRegression(max_iter=2000, class_weight="balanced"),
    )
    return model.fit(texts, labels)


def rates(y_true, y_pred):
    tp = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 1)
    fn = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 0)
    fp = sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p == 1)
    tn = sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p == 0)
    recall = tp / (tp + fn) if tp + fn else float("nan")      # Angriffe erkannt
    fpr = fp / (fp + tn) if fp + tn else float("nan")         # Harmlose fälschlich geblockt
    precision = tp / (tp + fp) if tp + fp else float("nan")
    return recall, fpr, precision, tp + fn, fp + tn


def line(name, y_true, y_pred):
    recall, fpr, precision, n_mal, n_ben = rates(y_true, y_pred)
    print(f"  {name:<28} Angriffe erkannt {recall:6.1%} (n={n_mal:<4}) | "
          f"Harmlose fälschlich geblockt {fpr:6.1%} (n={n_ben:<4}) | Precision {precision:6.1%}")


own_train, own_test = load_own(OWN)
ds = load_dataset("deepset/prompt-injections")
dp_train_x, dp_train_y = list(ds["train"]["text"]), list(ds["train"]["label"])
dp_test_x, dp_test_y = list(ds["test"]["text"]), list(ds["test"]["label"])

own_train_x, own_train_y = [r["text"] for r in own_train], [r["y"] for r in own_train]
own_test_x, own_test_y = [r["text"] for r in own_test], [r["y"] for r in own_test]

print(f"Eigene Daten: {len(own_train)} train / {len(own_test)} test | "
      f"deepset: {len(dp_train_x)} train / {len(dp_test_x)} test\n")

variants = {
    "A: nur eigene Daten": (own_train_x, own_train_y),
    "B: nur deepset": (dp_train_x, dp_train_y),
    "C: eigene + deepset": (own_train_x + dp_train_x, own_train_y + dp_train_y),
}

models = {}
for name, (x, y) in variants.items():
    models[name] = fit(x, y)
    print(name)
    line("auf eigenem Test", own_test_y, models[name].predict(own_test_x))
    line("auf deepset-Test", dp_test_y, models[name].predict(dp_test_x))
    print()

# Aufschlüsselung für Variante C auf dem eigenen Test-Set
print("Variante C, eigener Test, nach Sprache:")
pred = models["C: eigene + deepset"].predict(own_test_x)
for lang in sorted({r["language"] for r in own_test}):
    idx = [i for i, r in enumerate(own_test) if r["language"] == lang]
    line(lang, [own_test_y[i] for i in idx], [pred[i] for i in idx])

print("\nVariante C, eigener Test, nach Angriffskategorie (nur Angriffe):")
cats = collections.defaultdict(list)
for i, r in enumerate(own_test):
    if r["y"] == 1:
        cats[r["category"]].append(pred[i])
for cat, ps in sorted(cats.items()):
    print(f"  {cat:<24} erkannt {sum(ps) / len(ps):6.1%} (n={len(ps)})")

print("\nVariante C, eigener Test, Fehler:")
for r, p in zip(own_test, pred):
    if p != r["y"]:
        art = "VERPASST" if r["y"] == 1 else "FALSCH GEBLOCKT"
        print(f"  [{art}] {r['language']}/{r['category']}: {r['text'][:140]!r}")

print("\nVariante C, die 20 stärksten Merkmale für 'Angriff':")
_m = models["C: eigene + deepset"]
_names = _m.named_steps["tfidfvectorizer"].get_feature_names_out()
_coef = _m.named_steps["logisticregression"].coef_[0]
print("  " + " | ".join(repr(_names[i]) for i in np.argsort(_coef)[-20:][::-1]))
