# progress.md

Stand: 2026-10-30, Abschluss. Alle Schritte gelaufen; offen sind nur Punkte, die beim Nutzer liegen.

## Plan

| Schritt | Status |
|---|---|
| S0 Sicherungs-Commit | erledigt (`ebb022a` und je ein Commit pro Etappe, lokal) |
| S1 CLAUDE.md | erledigt |
| S2 Schema-/Leakage-Check + Tests | erledigt (1 Korrektur) |
| S3 Externe Quellen | erledigt; Eintrag in THIRD_PARTY_NOTICES.md offen (Nutzer) |
| S4 Handgeschriebene Zeilen | erledigt: fresh_raw1 + fresh_raw2; roleplay 11–12 statt 15 pro Sprache |
| S5 Build | erledigt: 609 Zeilen, sha256 `242a68c2…` |
| S6 Leakage | erledigt: 161 Leak-Zeilen vorher entfernt, danach 0 Treffer |
| S7 Auswertung | erledigt, einmal, pro Sprache parallel |
| S8 Bericht | erledigt: `reports/eval_2026-10-30.md`, Zahlen-Check 0 Probleme |
| S9 Abschluss | erledigt: pytest 168 passed, checks.md, DEVLOG-Entwurf |

## Outputs

- Test-Set: `datasets/test_fresh/test_fresh.jsonl`, `build_report.json`, `removed_by_leakage.jsonl`, `SOURCES.md`, `README.md`, `handwritten_{de,fr,it,en}.jsonl`, `raw/` (Gandalf, fresh_raw1.txt, fresh_raw2.txt)
- Bericht: `reports/eval_2026-10-30.md`, Rohdaten `reports/raw/eval_{de,en,fr,it}_2026-10-30.json`, `reports/leakage_2026-10-30.json`
- Entwürfe: `reports/devlog_draft.md`, `reports/third_party_notices_draft.md`
- Harness: `plan.md`, `checks.md`, `progress.md`, `CLAUDE.md`
- Scripts: `check_claude_md.py`, `check_schema.py`, `check_leakage.py`, `fetch_gandalf.py`, `convert_fresh_raw.py`, `build_test_fresh.py`, `eval_test_fresh.py`, `check_report_numbers.py`
- Tests: `tests/test_fresh_tools.py`, `tests/test_fresh_eval.py`

## Ergebnis (rules only, Schwelle 25)

| Sprache | Angriffe erkannt | Harmlose geblockt |
|---|---|---|
| de | 1/70 | 1/70 |
| en | 19/119 (Gandalf 15/50, handgeschrieben 4/69) | 0/70 |
| fr | 1/70 | 0/70 |
| it | 0/70 | 0/70 |

## Entscheidungen

- Die Texte schreibt der Nutzer selbst (Option a; für fresh_raw2 am 2026-10-30 bestätigt).
- Der benign-Untertyp steht in `note`; roleplay hat der Nutzer in der Quelldatei markiert.
- hackaprompt wird nicht verwendet (schon im Training). Gandalf: 50 Zeilen, alle `instruction_override`, Seed 20261030.
- 161 Leak-Zeilen wurden vor der Auswertung entfernt (A5). Danach wurde das Set nicht mehr verändert.
- Ausgewertet sind nur die Regeln, mit fester Schwelle 25.
- Der Nutzer wollte erst Ersatz-Zeilen schreiben, statt mit den kleinen Zellen auszuwerten.
- Nach der Auswertung kam `by_source` dazu; alle übrigen Werte sind belegt identisch.

## Offene Punkte

1. `reports/third_party_notices_draft.md` in `THIRD_PARTY_NOTICES.md` übernehmen (Nutzer).
2. `reports/devlog_draft.md` prüfen und in `DEVLOG.md` übernehmen (Nutzer).
3. Auf diesem Set auch das XLM-R-Modell auswerten, bevor jemand Regeln auf die Fehler hin anpasst. Dafür braucht es eine torch-Umgebung und das Modell aus `../apertus/xlmr-detector/`. Der Leakage-Check muss dann zusätzlich gegen die apertus-Trainingsdateien laufen (`--block`).
4. `fresh_raw1.txt`/`fresh_raw2.txt` im Hauptordner sind nicht committet; Kopien liegen in `datasets/test_fresh/raw/`.
5. Kein Push (nicht freigegeben).

## Nächste Aktion

Keine im Rahmen dieses Harness. Ein Folgeauftrag wäre Punkt 3.
