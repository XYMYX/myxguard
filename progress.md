# progress.md

Stand: 2026-10-30, Abschluss inklusive XLM-R-Zusatz.

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
| S9 Abschluss | erledigt: checks.md, DEVLOG-Entwurf |
| X1 XLM-R-Zusatz | erledigt: gleiche Daten, argmax, ohne Installation (`../apertus/.venv`); Leakage vollständig (extra_train war nie im Training, per Log belegt) |

## Outputs

- Test-Set: `datasets/test_fresh/test_fresh.jsonl`, `build_report.json`, `removed_by_leakage.jsonl`, `SOURCES.md`, `README.md`, `handwritten_{de,fr,it,en}.jsonl`, `raw/` (Gandalf, fresh_raw1.txt, fresh_raw2.txt)
- Bericht: `reports/eval_2026-10-30.md`, Rohdaten `reports/raw/eval_{de,en,fr,it}_2026-10-30.json` und `reports/raw/eval_xlmr_{de,en,fr,it}_2026-10-30.json`, `reports/leakage_2026-10-30.json`, `reports/leakage_xlmr_2026-10-30.json`
- Entwürfe: `reports/devlog_draft.md`, `reports/third_party_notices_draft.md`
- Harness: `plan.md`, `checks.md`, `progress.md`, `CLAUDE.md`
- Scripts: `check_claude_md.py`, `check_schema.py`, `check_leakage.py`, `fetch_gandalf.py`, `convert_fresh_raw.py`, `build_test_fresh.py`, `eval_test_fresh.py`, `eval_test_fresh_xlmr.py`, `check_report_numbers.py`
- Tests: `tests/test_fresh_tools.py`, `tests/test_fresh_eval.py`

## Ergebnis

| Sprache | Regeln: Angriffe erkannt | Regeln: harmlos geblockt | XLM-R: Angriffe erkannt | XLM-R: harmlos geblockt | XLM-R: Rollenspiel geblockt |
|---|---|---|---|---|---|
| de | 1/70 | 1/70 | 50/70 | 4/70 | 2/11 |
| en | 19/119 | 0/70 | 101/119 | 7/70 | 3/12 |
| fr | 1/70 | 0/70 | 44/70 | 4/70 | 1/12 |
| it | 0/70 | 0/70 | 43/70 | 4/70 | 1/12 |

## Entscheidungen

- Die Texte schreibt der Nutzer selbst (Option a; für fresh_raw2 am 2026-10-30 bestätigt).
- Der benign-Untertyp steht in `note`; roleplay hat der Nutzer in der Quelldatei markiert.
- hackaprompt wird nicht verwendet (schon im Training). Gandalf: 50 Zeilen, alle `instruction_override`, Seed 20261030.
- 161 Leak-Zeilen wurden vor der Auswertung entfernt (A5). Danach wurde das Set nicht mehr verändert.
- Hauptteil: Regeln mit fester Schwelle 25; XLM-R als Zusatz (siehe unten).
- Der Nutzer wollte erst Ersatz-Zeilen schreiben, statt mit den kleinen Zellen auszuwerten.
- Nach der Auswertung kam `by_source` dazu; alle übrigen Werte sind belegt identisch.
- XLM-R wurde auf Wunsch des Nutzers ausgewertet: argmax, kein Training, nichts installiert. Gegenprobe und zweiter Lauf bestanden.

## Offene Punkte

1. `reports/third_party_notices_draft.md` in `THIRD_PARTY_NOTICES.md` übernehmen (Nutzer).
2. `reports/devlog_draft.md` prüfen und in `DEVLOG.md` übernehmen (Nutzer).
3. Die 236 v8-Zeilen gibt es nirgends: Repo, Git-Verlauf (lokal und GitHub), Papierkorb, VS-Code-/Cursor-Verlauf und Claude-Transkripte durchsucht. Sie waren in keinem Lauf vom 2026-10-29 im Training. Der DEVLOG-Eintrag vom 2026-10-29 behauptet dazu eine Wirkung, die nie getestet wurde. Korrektur steht im DEVLOG-Entwurf (Nutzer).
4. `fresh_raw1.txt`/`fresh_raw2.txt` im Hauptordner sind nicht committet; Kopien liegen in `datasets/test_fresh/raw/`.
5. Kein Push (nicht freigegeben).

## Nächste Aktion

Keine im Rahmen dieses Harness.
