# checks.md

Stand: 2026-10-30. Urteil: pass, fail oder unresolved. Fehlende Belege bleiben sichtbar.

| Schritt | Anforderung | Urteil | Beleg |
|---|---|---|---|
| S0 | Sicherungs-Commit vor riskanten Änderungen vorgeschlagen | unresolved | vorgeschlagen, wartet auf OK; noch kein Commit |
| S1 | CLAUDE.md existiert und enthält jede Projektregel | pass | `python scripts/check_claude_md.py` → `rules 7/7`, Exit 0 |
| S1 | CLAUDE.md listet jedes Script und jeden neuen Test | pass | dasselbe Script → `tools listed 6/6` |
| S2 | Schema-Check lehnt fehlende Felder, falsche Werte und Zusatzfelder ab | pass | `tests/test_fresh_tools.py` (3 Schema-Tests) grün im Ersatz-Runner |
| S2 | Leakage-Check erkennt exakte Kopien, Ein-Wort-Änderungen, Akzent-/Gross-Klein-Varianten und interne Duplikate; lässt fremden Text durch | pass | `tests/test_fresh_tools.py` (5 Leakage-Tests) grün im Ersatz-Runner: 8 passed, 0 failed |
| S2 | Leakage-Check meldet bei leerem Set nicht "bestanden" | pass | `python scripts/check_leakage.py` → `0 rows in test_fresh: nothing checked`, Exit 1 |
| S2 | Neue Tests laufen unter pytest | unresolved | pytest nicht installiert (B5); nur der Ersatz-Runner ist gelaufen |
| S3 | Externe Quellen geholt, Lizenz pro Quelle in SOURCES.md | unresolved | Download nicht freigegeben |
| S4 | Vorlagen für handgeschriebene Zeilen pro Sprache | pass | `datasets/test_fresh/handwritten_{de,fr,it,en}.jsonl` (leer) + `README.md`; `check_schema.py` Exit 0 |
| S4 | Zielzahlen pro Sprache × Kategorie (A3) | unresolved | 0 Zeilen geschrieben |
| S5 | test_fresh.jsonl gebaut, Schema grün, alle 4 Sprachen × 4 Kategorien vorhanden | unresolved | noch nicht begonnen |
| S6 | Leakage-Check 0 Treffer auf der gespeicherten Version | unresolved | noch keine Zeilen |
| S7 | Precision, Recall, F1 pro Sprache und pro Kategorie | unresolved | noch nicht ausgewertet |
| S7 | Fehlalarm-Rate auf benign pro Sprache | unresolved | noch nicht ausgewertet |
| S7 | Confusion Matrix | unresolved | noch nicht ausgewertet |
| S7 | ≥ 10 Fehlbeispiele pro Sprache | unresolved | noch nicht ausgewertet |
| S8 | Zahlen im Bericht stimmen mit den Rohdaten überein | unresolved | noch nicht begonnen |
| S9 | Bestehende Tests (pytest) weiterhin grün | unresolved | pytest nicht installiert (B5) |
