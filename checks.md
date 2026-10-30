# checks.md

Stand: 2026-10-30. Urteil: pass, fail oder unresolved. Fehlende Belege bleiben sichtbar.

| Schritt | Anforderung | Urteil | Beleg |
|---|---|---|---|
| S0 | Sicherungs-Commit vor riskanten Änderungen | pass | lokaler Commit `ebb022a`, kein Push |
| S1 | CLAUDE.md existiert und enthält jede Projektregel | pass | `python scripts/check_claude_md.py` → `rules 7/7`, Exit 0 |
| S1 | CLAUDE.md listet jedes Script und jeden neuen Test | pass | dasselbe Script → `tools listed 6/6` |
| S2 | Schema-Check lehnt fehlende Felder, falsche Werte und Zusatzfelder ab | pass | `tests/test_fresh_tools.py` (3 Schema-Tests) grün im Ersatz-Runner |
| S2 | Leakage-Check erkennt exakte Kopien, Ein-Wort-Änderungen, Akzent-/Gross-Klein-Varianten und interne Duplikate; lässt fremden Text durch | pass | `tests/test_fresh_tools.py` (5 Leakage-Tests) grün im Ersatz-Runner: 8 passed, 0 failed |
| S2 | Leakage-Check meldet bei leerem Set nicht "bestanden" | pass | `python scripts/check_leakage.py` → `0 rows in test_fresh: nothing checked`, Exit 1 |
| S2 | Neue Tests laufen unter pytest | pass | pytest 8.4.2: Gesamtlauf `156 passed in 7.03s`, inklusive der 8 neuen Tests |
| S2 | Leakage-Check läuft mit fremden Zeichen und mit Zeilen, die nach dem Normalisieren leer sind | pass | Korrekturversuch 1/3: `tests/test_fresh_tools.py` 9 passed; Lauf auf dem Gandalf-Rohpool ohne Absturz |
| S3 | Externe Quelle geholt, Revision festgehalten | pass | `scripts/fetch_gandalf.py` → 1000 Zeilen (777/111/112 = erwartet), Revision `04737b65` vor und nach dem Download gleich (`raw/gandalf_ignore_instructions.meta.json`) |
| S3 | Lizenz pro Quelle in SOURCES.md, mit Open Source vereinbar | pass | `datasets/test_fresh/SOURCES.md`: MIT laut Card; Notices-Entwurf in `reports/third_party_notices_draft.md` |
| S3 | Quelle ist nicht im Training | pass | `git grep -i gandalf` in train/dev/eval/training: 0 Treffer; Leakage-Vorcheck: 0 Treffer gegen alle Sperrdateien |
| S3 | Lizenz in THIRD_PARTY_NOTICES.md eingetragen | unresolved | Datei liegt ausserhalb der erlaubten Pfade; der Nutzer trägt den Entwurf ein |
| S4 | Vorlagen für handgeschriebene Zeilen pro Sprache | pass | `datasets/test_fresh/handwritten_{de,fr,it,en}.jsonl` (leer) + `README.md`; `check_schema.py` Exit 0 |
| S4 | Handgeschriebene Zeilen vorhanden, Format gültig | pass | `fresh_raw1.txt` (sha256 `e6070ede…`, Kopie in `raw/`): 360 Zeilen, 0 fehlerhafte Zeilen, 0 exakte Duplikate; `convert_fresh_raw.py` → 4 × 90 Zeilen |
| S4 | Zielzahlen pro Sprache × Kategorie (A3) | fail | Nach dem Entfernen der Leak-Zeilen 23 Zellen unter dem Ziel: pro Sprache 8–9 Angriffe pro Kategorie (Ziel 15), 25 benign (Ziel 45), 1–2 roleplay (Ziel 15), 8–9 hard_negative (Ziel 15); siehe `build_report.json` |
| S5 | test_fresh.jsonl gebaut, Schema grün | pass | Teil-Set: `build_test_fresh.py` → 50 Zeilen (nur Gandalf, en/instruction_override), sha256 `016de0110ab1…`; `check_schema.py` Exit 0 |
| S5 | Zählungen im build_report = Zeilen in der Datei | pass | 50 = 50 = Summe von by_language_category |
| S5 | Build ist reproduzierbar | pass | zweiter Lauf, gleicher sha256 `016de0110ab1` |
| S5 | Alle 4 Sprachen × 4 Kategorien vorhanden | pass | 249 Zeilen, sha256 `277061e16a9b`; jede Zelle hat ≥ 8 Zeilen (`build_report.json`) |
| S6 | Leak-Zeilen vor der Auswertung entfernt und gezählt (A5) | pass | 161 von 360 handgeschriebenen Zeilen entfernt: 160 exakt aus `../apertus/test_fresh.jsonl`, 1 jaccard aus `train.jsonl`; Liste in `datasets/test_fresh/removed_by_leakage.jsonl` |
| S6 | Leakage-Check 0 Treffer auf der gespeicherten Version | pass | `check_leakage.py` → 249 Zeilen, 0 Treffer; `reports/leakage_2026-10-30.json` nennt sha256 `277061e16a9b…` |
| S7 | Auswertungs-Script berechnet Confusion Matrix, P/R/F1, FPR, Werte pro Kategorie (one-vs-benign) und Untertyp sowie Wilson-Intervalle korrekt | pass | `tests/test_fresh_eval.py`: 10 passed auf synthetischen Zeilen mit von Hand ausgerechneten Werten |
| S7 | Auswertung startet nicht ohne passenden Leakage-Bericht und nicht auf einem Teil-Set | pass | Tests `test_leakage_gate`, `test_coverage_gate_refuses_partial_set`; Lauf `eval_test_fresh.py --lang en` → 7× `refused`, Exit 1, keine Datei geschrieben |
| S7 | Precision, Recall, F1 pro Sprache und pro Kategorie | unresolved | noch nicht ausgewertet |
| S7 | Fehlalarm-Rate auf benign pro Sprache | unresolved | noch nicht ausgewertet |
| S7 | Confusion Matrix | unresolved | noch nicht ausgewertet |
| S7 | ≥ 10 Fehlbeispiele pro Sprache | unresolved | noch nicht ausgewertet |
| S8 | Zahlen-Check erkennt eine falsche Zahl und einen fehlenden SHA-256 | pass | `test_report_numbers_must_come_from_raw_json` |
| S8 | Zahlen im Bericht stimmen mit den Rohdaten überein | unresolved | noch kein Bericht |
| S9 | Bestehende Tests (pytest) weiterhin grün | unresolved | Zwischenstand 2026-10-30: `python -m pytest -q` → 167 passed, Exit 0. Der Abschlusslauf nach S8 steht noch aus |
