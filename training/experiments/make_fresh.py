"""Wandelt fresh_raw.txt in test_fresh.jsonl um.

Eine Zeile pro Text im Format:  sprache|label|kategorie|text
Beispiele fürs Format (keine Vorlagen zum Abschreiben):
de|malicious|data_exfiltration|Beispieltext
fr|benign|plain|Beispieltext
Zeilen mit # am Anfang und leere Zeilen werden übersprungen.
label: malicious oder benign. kategorie: instruction_override, data_exfiltration, jailbreak_persona, plain oder hard_negative.
"""
import json

n = 0
with open("fresh_raw.txt", encoding="utf-8") as f, open("test_fresh.jsonl", "w", encoding="utf-8") as out:
    for i, line in enumerate(f, 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("|", 3)
        if len(parts) != 4 or parts[1] not in ("malicious", "benign") or parts[0] not in ("de", "fr", "it", "en"):
            print(f"Zeile {i} übersprungen (Format prüfen): {line[:60]!r}")
            continue
        lang, label, cat, text = (p.strip() for p in parts)
        out.write(json.dumps({"text": text, "label": label, "language": lang, "category": cat}, ensure_ascii=False) + "\n")
        n += 1
print(f"{n} Texte in test_fresh.jsonl geschrieben")
