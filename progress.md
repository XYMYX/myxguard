# progress.md

Stand: 2026-10-30, nach Etappe 1 (Plan + Prüf-Tools).

## Plan

| Schritt | Status |
|---|---|
| S0 Sicherungs-Commit | blockiert: wartet auf OK |
| S1 CLAUDE.md | erledigt |
| S2 Schema-/Leakage-Check + Tests | erledigt (pytest-Lauf offen, B5) |
| S3 Externe Quellen | blockiert: Download-Freigabe für `Lakera/gandalf_ignore_instructions` |
| S4 Handgeschriebene Zeilen | Vorlage erledigt; Inhalt blockiert: der Nutzer schreibt de/fr/it/en |
| S5 bis S9 | wartet auf S3/S4 |

## Outputs

- `plan.md`
- `CLAUDE.md`
- `checks.md`
- `scripts/check_claude_md.py`, `scripts/check_schema.py`, `scripts/check_leakage.py`
- `tests/test_fresh_tools.py`
- `datasets/test_fresh/README.md`, `datasets/test_fresh/handwritten_{de,fr,it,en}.jsonl` (leer)

## Entscheidungen

- Die de/fr/it-Texte schreibt der Nutzer von Hand (Antwort auf die offene Frage, Option a). Claude schreibt keine Test-Texte.
- Kein neues Feld `subtype`. Der benign-Untertyp steht in `note`, damit das Schema gleich bleibt wie in train/dev/eval.
- hackaprompt wird nicht als "unbenutzte" Quelle verwendet, weil es schon in train und heldout steckt.
- Ein leeres Set gilt im Leakage-Check als Fehler und nicht als "0 Treffer".
- Ausgewertet wird rules-only mit Schwelle 25 (A1). XLM-R kommt nur dazu, wenn der Nutzer eine Umgebung mit torch nennt.

## Offene Punkte

1. Freigabe für den S0-Commit (lokal).
2. Freigabe für den Download von `Lakera/gandalf_ignore_instructions`. Die Grösse kommt vor dem Download.
3. Freigabe für `pip install pytest`, sonst bleiben die pytest-Checks `unresolved`.
4. Handgeschriebene Zeilen in `datasets/test_fresh/handwritten_*.jsonl`.

## Nächste Aktion

Nach Freigabe 2: S3 (Download, SOURCES.md, Entwurf der Notices). Sobald Zeilen da sind: S5 → S6 → S7.
