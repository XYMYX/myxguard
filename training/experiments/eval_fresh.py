"""Frisches Test-Set auswerten (nur Auswertung, kein Training).

Datei test_fresh.jsonl, eine Zeile pro Text, zum Beispiel:
{"text": "...", "label": "malicious", "language": "de", "category": "data_exfiltration"}
{"text": "...", "label": "benign", "language": "fr", "category": "plain"}

Regeln:
- Selbst oder von Bekannten schreiben, nicht mit einem Modell erzeugen und nichts aus den Trainingsdaten kopieren.
- Nicht zum Training oder Abstimmen verwenden. Ansehen und auswerten erst am Ende, einmal.

Aufruf: python eval_fresh.py [test_fresh.jsonl]
"""
import collections, json, sys

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

PATH = "xlmr-detector"
DATA = sys.argv[1] if len(sys.argv) > 1 else "test_fresh.jsonl"

tok = AutoTokenizer.from_pretrained(PATH)
model = AutoModelForSequenceClassification.from_pretrained(PATH).to("cuda").eval()

with open(DATA, encoding="utf-8") as f:
    rows = [json.loads(l) for l in f if l.strip()]
texts = [r["text"] for r in rows]

preds = []
for i in range(0, len(texts), 32):
    enc = tok(texts[i:i + 32], truncation=True, max_length=256, padding=True, return_tensors="pt").to("cuda")
    with torch.no_grad():
        preds.extend(model(**enc).logits.argmax(-1).tolist())


def report(name, idx):
    mal = [i for i in idx if rows[i]["label"] == "malicious"]
    ben = [i for i in idx if rows[i]["label"] != "malicious"]
    rec = sum(preds[i] for i in mal) / len(mal) if mal else float("nan")
    fpr = sum(preds[i] for i in ben) / len(ben) if ben else float("nan")
    print(f"  {name:<24} Angriffe erkannt {rec:6.1%} (n={len(mal):<3}) | Harmlose geblockt {fpr:6.1%} (n={len(ben):<3})")


print(f"{len(rows)} Texte aus {DATA}")
report("alle", list(range(len(rows))))
print("nach Sprache:")
for lang in sorted({r["language"] for r in rows}):
    report(lang, [i for i, r in enumerate(rows) if r["language"] == lang])
print("nach Kategorie:")
for cat in sorted({r["category"] for r in rows}):
    report(cat, [i for i, r in enumerate(rows) if r["category"] == cat])

print("Fehler:")
for r, p in zip(rows, preds):
    if (p == 1) != (r["label"] == "malicious"):
        art = "VERPASST" if r["label"] == "malicious" else "FALSCH GEBLOCKT"
        print(f"  [{art}] {r['language']}/{r['category']}: {r['text'][:140]!r}")
