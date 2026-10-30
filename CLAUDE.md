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
| `scripts/fetch_gandalf.py` | Lädt `Lakera/gandalf_ignore_instructions` als JSON nach `datasets/test_fresh/raw/` und hält die Revision fest. Nur mit Download-Freigabe. | aktiv |
| `tests/test_fresh_tools.py` | Tests für den Schema- und den Leakage-Check | aktiv |
| `scripts/build_test_fresh.py` | Baut `datasets/test_fresh/test_fresh.jsonl` und `build_report.json`: Gandalf-Stichprobe (50, Seed 20261030) plus handgeschriebene Zeilen. Führt den Detektor nie aus. | aktiv |
| `scripts/eval_test_fresh.py` | Auswertung pro Sprache (`--lang de|fr|it|en|all`) → `reports/raw/eval_<lang>_<datum>.json`. Schwelle fest 25. Läuft nur, wenn der Leakage-Bericht den aktuellen SHA-256 mit 0 Treffern nennt **und** jede Sprache Angriffe und benign-Zeilen hat. | aktiv, noch nie auf test_fresh gelaufen |
| `scripts/check_report_numbers.py` | Prüft jede Zahl in den Tabellen von `reports/eval_<datum>.md` gegen die Roh-JSONs und ob der Bericht den SHA-256 des Sets nennt. Fliesstext prüft es nicht, und eine falsche Zahl, die zufällig einem anderen Rohwert gleicht, fällt nicht auf. | aktiv |
| `tests/test_fresh_eval.py` | Tests für Metriken, Wilson-Intervall, beide Gates und den Zahlen-Check, nur auf synthetischen Zeilen | aktiv |

Gesamte Suite: `python -m pytest -q`. Im Moment ist pytest nicht installiert (Blocker B5).

## Regel-Log (Layer 6)

Jeder Fehler und jede Korrektur bekommt hier eine Regel, damit es nicht wieder passiert.

- 2026-10-30: Bei leeren Dateien hat der Leakage-Check "0 Treffer" gemeldet, ohne etwas zu prüfen. Jetzt gilt 0 Zeilen als Fehler (Exit 1). Ein Check, der nichts prüft, gilt nie als bestanden.
- 2026-10-30: Der Leakage-Check ist auf der Windows-Konsole (cp1252) beim Ausgeben fremder Zeichen abgestürzt. Scripts, die Fremdtext ausgeben, setzen `sys.stdout.reconfigure(errors="replace")`.
- 2026-10-30: Eine Zeile, die nach dem Normalisieren leer ist (z. B. nur chinesische Schrift), wurde als Treffer "gegen train.jsonl" gemeldet. Solche Zeilen heissen jetzt `unchecked` und zählen weiter als Treffer, nie als sauber.
- 2026-10-30: Wenn der Leakage-Check die gebaute Datei und die Quelldateien zusammen prüft, meldet er jede Zeile als Duplikat ihrer selbst. Sobald `test_fresh.jsonl` existiert, prüft er nur diese Datei.
- 2026-10-30: Ausgewertet wird das Test-Set erst, wenn alle vier Sprachen da sind, und nur einmal. Kein Zwischenlauf auf einem Teil-Set. Seit 2026-10-30 erzwingt das `coverage_gate` in `eval_test_fresh.py`; vorher hätte das Leakage-Gate das Teil-Set durchgelassen.
- 2026-10-30: Tests lesen nie `test_fresh.jsonl`. Ein Test, der vom aktuellen Stand des Sets abhängt, wird rot, sobald das Set fertig ist, und würde das Set nebenbei ansehen.
- 2026-10-30: hackaprompt steckt schon in train und heldout. Eine Quelle gilt erst als "unbenutzt", wenn `git grep <name> datasets/ training/` nichts findet.
