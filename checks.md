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
| S4 | Zielzahlen pro Sprache × Kategorie (A3) | unresolved | 0 Zeilen geschrieben |
| S5 | test_fresh.jsonl gebaut, Schema grün | pass | Teil-Set: `build_test_fresh.py` → 50 Zeilen (nur Gandalf, en/instruction_override), sha256 `016de0110ab1…`; `check_schema.py` Exit 0 |
| S5 | Zählungen im build_report = Zeilen in der Datei | pass | 50 = 50 = Summe von by_language_category |
| S5 | Build ist reproduzierbar | pass | zweiter Lauf, gleicher sha256 `016de0110ab1` |
| S5 | Alle 4 Sprachen × 4 Kategorien vorhanden | fail | 23 Zellen unter dem Ziel; nur en/instruction_override hat Zeilen. Wartet auf die handgeschriebenen Zeilen (kein Fix durch Claude möglich) |
| S6 | Leakage-Check 0 Treffer auf der gespeicherten Version | unresolved | Teil-Set: 0 Treffer auf sha256 `016de0110ab1` (`reports/leakage_2026-10-30.json`). Muss auf dem vollständigen Set neu laufen |
| S7 | Precision, Recall, F1 pro Sprache und pro Kategorie | unresolved | noch nicht ausgewertet |
| S7 | Fehlalarm-Rate auf benign pro Sprache | unresolved | noch nicht ausgewertet |
| S7 | Confusion Matrix | unresolved | noch nicht ausgewertet |
| S7 | ≥ 10 Fehlbeispiele pro Sprache | unresolved | noch nicht ausgewertet |
| S8 | Zahlen im Bericht stimmen mit den Rohdaten überein | unresolved | noch nicht begonnen |
| S9 | Bestehende Tests (pytest) weiterhin grün | unresolved | Zwischenstand 2026-10-30: `python -m pytest -q` → 156 passed, Exit 0. Der Abschlusslauf nach S8 steht noch aus |
