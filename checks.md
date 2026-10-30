# checks.md

Stand: 2026-10-30, Abschluss. Urteil: pass, fail oder unresolved. Fehlende Belege bleiben sichtbar.
Alle Checks unten liefen gegen `datasets/test_fresh/test_fresh.jsonl` mit sha256 `242a68c227e01d0d…` (Commit `7570c3a`, unverändert seither).

| Schritt | Anforderung | Urteil | Beleg |
|---|---|---|---|
| S0 | Sicherungs-Commit vor riskanten Änderungen | pass | lokaler Commit `ebb022a`, danach pro Etappe ein Commit; nie gepusht |
| S1 | CLAUDE.md existiert und enthält jede Projektregel | pass | `python scripts/check_claude_md.py` → `rules 7/7` |
| S1 | CLAUDE.md listet jedes Script und jeden neuen Test | pass | dasselbe Script → `tools listed 12/12` |
| S2 | Schema-Check lehnt fehlende Felder, falsche Werte und Zusatzfelder ab | pass | `tests/test_fresh_tools.py` (3 Schema-Tests) |
| S2 | Leakage-Check erkennt exakte Kopien, Ein-Wort-Änderungen, Akzent-/Gross-Klein-Varianten, interne Duplikate und nicht prüfbare Zeilen | pass | `tests/test_fresh_tools.py` (6 Leakage-Tests) |
| S2 | Leakage-Check meldet bei leerem Set nicht "bestanden" | pass | Lauf auf leeren Vorlagen → Exit 1 (Korrektur, Regel in CLAUDE.md) |
| S2 | Leakage-Check läuft mit fremden Zeichen auf der Windows-Konsole | pass | Korrekturversuch 1/3: `sys.stdout.reconfigure(errors="replace")`; Lauf auf dem Gandalf-Rohpool ohne Absturz |
| S3 | Externe Quelle geholt, Revision festgehalten | pass | `scripts/fetch_gandalf.py` → 1000 Zeilen (777/111/112), Revision `04737b65` vor und nach dem Download gleich |
| S3 | Lizenz pro Quelle notiert, mit Open Source vereinbar | pass | `datasets/test_fresh/SOURCES.md`: Gandalf MIT, handgeschrieben MIT |
| S3 | Quelle nicht im Training | pass | `git grep -i gandalf` in train/dev/eval/training: 0; Leakage-Vorcheck 0 Treffer gegen alle Sperrdateien |
| S3 | Lizenz in THIRD_PARTY_NOTICES.md eingetragen | unresolved | Datei liegt ausserhalb der erlaubten Pfade; Entwurf in `reports/third_party_notices_draft.md`, der Nutzer trägt ihn ein |
| S4 | Handgeschriebene Zeilen vorhanden, Format gültig | pass | `fresh_raw1.txt` (sha256 `e6070ede…`) + `fresh_raw2.txt` (`a2c79a3e…`), je 360 Zeilen, 0 fehlerhafte Zeilen; Kopien in `datasets/test_fresh/raw/` |
| S4 | Von Menschen geschrieben, nicht von einem Modell | pass | Angabe des Nutzers am 2026-10-30 (fresh_raw2: «Ich selbst»). Nicht technisch prüfbar |
| S4 | Zielzahlen pro Sprache × Kategorie (A3) | fail | 4 von 28 Zellen unter dem Ziel: roleplay de 11, en/fr/it 12 (Ziel 15). Alle anderen Zellen erfüllt (`build_report.json`) |
| S5 | test_fresh.jsonl gebaut, Schema grün | pass | 609 Zeilen; `check_schema.py` → 0 Fehler |
| S5 | Zählungen im build_report = Zeilen in der Datei | pass | 609 = Summe von `by_language_category` |
| S5 | Alle 4 Sprachen × 4 Kategorien vorhanden | pass | jede Zelle ≥ 23 Zeilen |
| S6 | Leak-Zeilen vor der Auswertung entfernt und gezählt (A5) | pass | 161 von 720 handgeschriebenen Zeilen entfernt (160 exakt aus dem alten Fresh-Set, 1 jaccard aus train), Liste in `datasets/test_fresh/removed_by_leakage.jsonl` |
| S6 | Leakage-Check 0 Treffer auf der gespeicherten Version | pass | `check_leakage.py` → 609 Zeilen, 0 Treffer; `reports/leakage_2026-10-30.json` nennt sha256 `242a68c2…` |
| S7 | Auswertung startet nur mit passendem Leakage-Bericht und vollständigem Set | pass | Tests `test_leakage_gate`, `test_coverage_gate_refuses_partial_set`; Probelauf auf dem Teil-Set → 7× `refused` |
| S7 | Auswertungs-Pipeline korrekt | pass | 11 Tests auf synthetischen Zeilen; Gegenprobe auf heldout: 79/186, Recall 0.425, 0 FP, identisch mit `scripts/benchmark.py` |
| S7 | Precision, Recall, F1 pro Sprache und pro Kategorie | pass | `reports/raw/eval_{de,en,fr,it}_2026-10-30.json`; Tabellen in `reports/eval_2026-10-30.md` |
| S7 | Fehlalarm-Rate auf harmlosen Texten pro Sprache | pass | de 1.4 %, en/fr/it 0.0 % (je n=70), dazu pro Untertyp |
| S7 | Confusion Matrix | pass | pro Sprache im Bericht und in den Roh-JSONs (`confusion`) |
| S7 | ≥ 10 Fehlbeispiele pro Sprache | pass | 10 pro Sprache im Bericht, nach fester Regel ausgewählt; alle Fehler (de 70, en 100, fr 69, it 70) in den Roh-JSONs |
| S7 | Nachträgliche Ergänzung `by_source` ändert keine Werte | pass | Vergleich erster/zweiter Lauf: alle Felder ausser `by_source` identisch |
| S8 | Tabellenzahlen stimmen mit den Rohdaten überein | pass | `check_report_numbers.py reports/eval_2026-10-30.md` → 0 Probleme |
| S8 | Zahlen im Fliesstext stimmen | pass | Prüfung per Script gegen die Roh-JSONs; 1 Fehler gefunden und korrigiert («67–68» → «66–68»), Regel in CLAUDE.md |
| S8 | Alle Zahlen berichtet, auch die schlechten | pass | Bericht und DEVLOG-Entwurf nennen pro Sprache Recall 0.0–16.0 %, Datenabfluss 0 von 23, Gandalf getrennt |
| S9 | Bestehende Tests (pytest) weiterhin grün | pass | `python -m pytest -q` → 169 passed, Exit 0 (156 bestehende + 13 neue) |
| S9 | DEVLOG-Entwurf erstellt, nicht eingetragen | pass | `reports/devlog_draft.md`; `DEVLOG.md` unverändert (`git status`) |
| — | Nur erlaubte Pfade geändert | pass | `git diff --stat 5cc31b5..HEAD`: nur `datasets/test_fresh/`, `reports/`, `scripts/`, `tests/test_fresh_*.py`, `plan.md`, `checks.md`, `progress.md`, `CLAUDE.md`, dazu `HARNESS.md` (Auftrag des Nutzers, nur committet) |
| X1 | XLM-R ausgewertet, ohne Installation | pass | `../apertus/.venv` (torch 2.11.0+cu128, transformers 5.21.0, CUDA); `scripts/eval_test_fresh_xlmr.py` → `reports/raw/eval_xlmr_{de,en,fr,it}_2026-10-30.json` |
| X1 | Leakage gegen die Trainingsdaten des Modells | pass | `reports/leakage_xlmr_2026-10-30.json`: 609 Zeilen gegen 7171 gesperrte Texte (zusätzlich dataset.jsonl, external_train.jsonl, external_benign_test.jsonl, deepset train und test), 0 Treffer |
| X1 | Leakage gegen **alle** Trainingsdaten des Modells | pass | Nachprüfung 2026-10-30: `extra_train.jsonl` war nie im Training. Log «Externe Trainingsdaten: 2183» = Zeilen in `external_train.jsonl`; 154 + 546 + 2183 = 2883 = Log-Summe (1928 + 955); `make_extra.py` 0 Bytes, auch in Commit `9b3faea` von `myxguard-datagen`; alle Trainingsdateien älter als der Lauf (23:42:43) |
| X1 | Welcher Seed | pass | Seed 3: `model.safetensors` und `log_train_3.txt` in derselben Sekunde geschrieben |
| X1 | Cut-off nicht auf dem Test-Set gewählt | pass | argmax wie in `eval_fresh.py`; Test `test_xlmr_rows_use_argmax_not_a_threshold` |
| X1 | Richtiges Modell, richtig geladen | pass | auf dem alten Fresh-Set 47/80 erkannt und 15/80 geblockt, innerhalb der DEVLOG-Spanne (50–60 % und 12.5–18.8 %) |
| X1 | Lauf deterministisch | pass | zweiter Lauf: gleiche Entscheidungen, maximale Score-Differenz 0.0 |
| X1 | Metriken, Fehlalarm-Raten, Confusion Matrix, ≥ 10 Fehlbeispiele pro Sprache | pass | Abschnitt «Zusatz: XLM-R» in `reports/eval_2026-10-30.md`; Fehler de 24, en 25, fr 30, it 31, je 10 gezeigt |
| X1 | Rollenspiel-Bitten nicht geblockt (Projektregel) | fail | XLM-R blockt 7 von 47 (de 2/11, en 3/12, fr 1/12, it 1/12). Das ist ein Befund über das Modell, kein Fehler der Auswertung |
| X1 | Zahlen im Bericht | pass | `check_report_numbers.py` → 0 Probleme gegen 8 Roh-Dateien; Fliesstext per Script geprüft (8/8 OK) |
| X1 | Regel-Tabellen durch den Zusatz unverändert | pass | neu erzeugte Regel-Tabellen byte-gleich mit der früheren Fassung (`diff -q`) |
