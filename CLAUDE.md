# CLAUDE.md – myxguard

Mehrsprachiger Prompt-Injection-Detektor (en/de/fr/it, Open Source, MIT).
Laufende Aufgabe: frisches Test-Set `datasets/test_fresh/` bauen und myxguard pro Sprache auswerten.
Auftrag: `HARNESS.md`. Plan: `plan.md`. Stand: `progress.md`. Prüfbericht: `checks.md`.

Beim Wiederaufnehmen zuerst diese Datei lesen, dann `plan.md` und `progress.md`.

## Projektregeln

- Kategorien im Test-Set: instruction_override, data_exfiltration, jailbreak_persona, benign.
- Alle vier Sprachen (en, de, fr, it): jede Sprache einzeln auswerten, nie nur ein Gesamtwert.
- Harmlose Rollenspiel-Bitten sind benign (z. B. «Spiel einen strengen Coach») und dürfen nicht geblockt werden.
- Test-Daten dürfen nie in train/dev/eval vorkommen, auch nicht leicht umformuliert. Der Leakage-Check nutzt `training/dedupe.py` (`NearDupIndex`).
- Fehlalarme zählen gleich viel wie erkannte Angriffe: Die Fehlalarm-Rate auf benign wird pro Sprache berichtet.
- Alle Zahlen berichten, auch die schlechten. Nichts schönrechnen.
- Lizenz jeder externen Quelle notieren (`datasets/test_fresh/SOURCES.md`). `THIRD_PARTY_NOTICES.md` darf ich nicht ändern, deshalb geht der Text als Entwurf nach `reports/third_party_notices_draft.md`.
- Nichts von Apertus erzeugen lassen. Die de/fr/it-Texte schreibt der Nutzer von Hand (Entscheidung vom 2026-10-30). Claude schreibt keine Test-Texte.
- Das Test-Set nie anpassen, um bessere Zahlen zu bekommen, und nie einen Check abschwächen. Leak-Zeilen werden nur vor der ersten Auswertung entfernt und gezählt.
- Ausgewertet wird der Detektor `myxguard.scan` mit fester Schwelle 25. Die Schwelle wird nicht auf dem Test-Set gesucht.

## Pfade

Erlaubt: `datasets/test_fresh/`, `reports/`, `scripts/`, `tests/` (nur neue Tests), `plan.md`, `checks.md`, `progress.md`, `CLAUDE.md`.
Nicht ändern: `datasets/train`, `datasets/dev`, `datasets/eval`, `training/`, `myxguard/`, `THIRD_PARTY_NOTICES.md`.
Ausserhalb des Repos nur lesen: `../apertus/test_fresh.jsonl` (altes, verbrauchtes Fresh-Set, gehört zur Sperrliste).

Ohne ausdrückliche Freigabe nicht erlaubt: Training, `git push`, Downloads (auch `pip install`). Vor riskanten Änderungen einen lokalen Commit vorschlagen. Nie zwei Sessions an derselben Datei.

## Schema

Pflichtfelder in jeder Zeile, wie in train/dev/eval: `text`, `label` (`malicious` | `benign`), `language`, `category`, `source`, `license`. Optional: `note`, darin bei benign der Untertyp: `plain`, `roleplay` oder `hard_negative`. Andere Felder gibt es nicht.

## Scripts und Tests

| Datei | Zweck | Status |
|---|---|---|
| `scripts/benchmark.py` | Bestehender Benchmark (Precision, Recall, FPR) | bestehend |
| `scripts/dataset_stats.py` | Bestehende Zählung pro Feld | bestehend |
| `scripts/check_claude_md.py` | Prüft, dass diese Datei jede Projektregel enthält und jedes Script/jeden Test auflistet | aktiv |
| `scripts/check_schema.py` | Schema-Check für `datasets/test_fresh/*.jsonl` | aktiv |
| `scripts/check_leakage.py` | Leakage-Check gegen train/dev/eval, samples, deepset_sample und das alte Fresh-Set, plus Duplikate innerhalb des Sets. Muss vor jeder Auswertung laufen. | aktiv |
| `tests/test_fresh_tools.py` | Tests für den Schema- und den Leakage-Check | aktiv |
| `scripts/build_test_fresh.py` | Baut `datasets/test_fresh/test_fresh.jsonl` | geplant (S5) |
| `scripts/eval_test_fresh.py` | Auswertung pro Sprache | geplant (S7) |
| `scripts/check_report_numbers.py` | Prüft die Zahlen im Bericht gegen die Rohdaten | geplant (S8) |

Gesamte Suite: `python -m pytest -q`. Im Moment ist pytest nicht installiert (Blocker B5).

## Regel-Log (Layer 6)

Jeder Fehler und jede Korrektur bekommt hier eine Regel, damit es nicht wieder passiert.

- 2026-10-30: Bei leeren Dateien hat der Leakage-Check "0 Treffer" gemeldet, ohne etwas zu prüfen. Jetzt gilt 0 Zeilen als Fehler (Exit 1). Ein Check, der nichts prüft, gilt nie als bestanden.
- 2026-10-30: hackaprompt steckt schon in train und heldout. Eine Quelle gilt erst als "unbenutzt", wenn `git grep <name> datasets/ training/` nichts findet.
