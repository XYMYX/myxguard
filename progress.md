# progress.md

Stand: 2026-10-30, nach Etappe 6 (handgeschriebene Zeilen, Leak-Bereinigung). Auswertung noch nicht gelaufen.

## Plan

| Schritt | Status |
|---|---|
| S0 Sicherungs-Commit | erledigt (`ebb022a`, lokal) |
| S1 CLAUDE.md | erledigt |
| S2 Schema-/Leakage-Check + Tests | erledigt; pytest 167 passed (Gesamtsuite) |
| S3 Externe Quellen | erledigt. Offen: Eintrag in THIRD_PARTY_NOTICES.md (Nutzer) |
| S4 Handgeschriebene Zeilen | erledigt: `fresh_raw1.txt` mit 360 Zeilen, davon 199 neu (161 Leaks entfernt) |
| S5 Build | erledigt: 249 Zeilen, sha256 `277061e16a9b` |
| S6 Leakage | erledigt: 0 Treffer auf 249 Zeilen |
| S7 Auswertung | Script + Tests fertig (`scripts/eval_test_fresh.py`); verweigert das Teil-Set; noch nie auf test_fresh gelaufen |
| S8 Bericht | Zahlen-Check fertig (`scripts/check_report_numbers.py`); Bericht wartet auf S7 |
| S9 | wartet |

## Outputs

- `plan.md`, `CLAUDE.md`, `checks.md`, `progress.md`
- `scripts/check_claude_md.py`, `scripts/check_schema.py`, `scripts/check_leakage.py`, `scripts/fetch_gandalf.py`, `scripts/build_test_fresh.py`
- `tests/test_fresh_tools.py` (9 Tests)
- `datasets/test_fresh/README.md`, `SOURCES.md`, `handwritten_{de,fr,it,en}.jsonl` (leer), `test_fresh.jsonl` (50 Zeilen, Teil-Set), `build_report.json`
- `datasets/test_fresh/raw/gandalf_ignore_instructions.jsonl`, `raw/gandalf_ignore_instructions.meta.json`
- `reports/third_party_notices_draft.md`, `reports/leakage_2026-10-30.json`

## Entscheidungen

- Die de/fr/it-Texte schreibt der Nutzer von Hand (Option a). Claude schreibt keine Test-Texte.
- Der benign-Untertyp steht in `note`.
- hackaprompt wird nicht verwendet (schon im Training).
- Ein leeres Set und Zeilen, die sich nicht prüfen lassen, gelten im Leakage-Check als Fehler.
- Ausgewertet wird rules-only mit Schwelle 25.
- Gandalf: alle Zeilen `instruction_override`, 50 Zeilen mit Seed 20261030 aus 910 (Freigabe des Nutzers, vor jedem Detektor-Lauf).
- Keine Auswertung auf dem Teil-Set: Jeder Blick auf Fehler würde das Set "verbrauchen" (DEVLOG 2026-10-29).

## Offene Punkte

0. **Entscheidung vor S7:** jetzt mit 8–9 Angriffen pro Kategorie und Sprache auswerten (verbraucht die 199 neuen Zeilen), oder erst die 160 alten Zeilen durch neue ersetzen.

1. Handgeschriebene Zeilen: 23 Zellen liegen unter dem Ziel (siehe `datasets/test_fresh/build_report.json`). en/instruction_override ist durch Gandalf schon gedeckt.
2. Den Entwurf aus `reports/third_party_notices_draft.md` in `THIRD_PARTY_NOTICES.md` übernehmen (Nutzer).

## Nächste Aktion

Sobald die Zeilen da sind: `python scripts/build_test_fresh.py` → `python scripts/check_schema.py` → `python scripts/check_leakage.py` → S7 `python scripts/eval_test_fresh.py --lang <xx>` (de/fr/it/en parallel) → S8 Bericht `reports/eval_<datum>.md` + `python scripts/check_report_numbers.py reports/eval_<datum>.md` → S9.
