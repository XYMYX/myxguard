# plan.md – Frisches Test-Set + Auswertung pro Sprache

Status: **freigegeben am 2026-10-30, offene Frage beantwortet: (a), die de/fr/it-Texte schreibt der Nutzer von Hand.** S1, S2 und die Vorlage aus S4 laufen. S0, S3 und der pytest-Teil warten auf die Freigaben 2–4.
Stand: 2026-10-30. Grundlage: HARNESS.md, README.md, DEVLOG.md, training/README.md, datasets/*/README.md, training/dedupe.py, scripts/benchmark.py, myxguard/benchmark.py, THIRD_PARTY_NOTICES.md.

## Befund aus dem Repo-Stand (vor dem Plan)

| # | Befund | Folge für den Plan |
|---|---|---|
| B1 | `CLAUDE.md`, `checks.md`, `progress.md` existieren nicht. | Werden in S1 / laufend neu angelegt. |
| B2 | **hackaprompt ist schon im Training** (`train.jsonl`: 10 Zeilen, `heldout.jsonl`: 16 Zeilen, via `training/public_rows.py`). | hackaprompt ist **keine** unbenutzte Quelle. Vorschlag: nicht verwenden. Falls doch: nur nach Leakage-Filter und mit Vermerk "Quelle teilweise im Training". |
| B3 | Lakera/gandalf_ignore_instructions ist nur Englisch. | de/fr/it-Angriffe brauchen andere Quellen oder handgeschriebene Zeilen (siehe offene Frage). |
| B4 | Im Repo liegt kein trainiertes Modell (`training/output/` fehlt). Ein XLM-R-Modell liegt ausserhalb: `../apertus/xlmr-detector/`. Es wurde auch auf `../apertus/dataset.jsonl`, `external_train.jsonl` u. a. trainiert, nicht nur auf `datasets/train`. | Rules-only (`myxguard`-Paket, Schwelle 25) ist ohne Download auswertbar. XLM-R nur, wenn eine Umgebung mit torch/transformers existiert; dann muss der Leakage-Check zusätzlich gegen die apertus-Trainingsdateien laufen (nur lesen). |
| B5 | `pytest` ist in keinem gefundenen Python installiert (3.12, 3.15); `torch` auch nicht. | Blocker für "pytest bleibt grün". Installation = Download → braucht Freigabe. |
| B6 | `THIRD_PARTY_NOTICES.md` ist nicht in den erlaubten Pfaden. | Lizenztexte werden als Entwurf in `reports/third_party_notices_draft.md` geschrieben; du trägst sie ein. |
| B7 | Bestehendes Schema: `text, label, language, category, source, license` (+ optional `note`). `myxguard/benchmark.py` verlangt `text, label, language, category, source`. | Schema-Check gegen genau diese Felder. |
| B8 | Altes Fresh-Set `../apertus/test_fresh.jsonl` (160 Zeilen) ist laut DEVLOG "verbraucht". | Wird als zusätzliche Sperrliste im Leakage-Check benutzt, damit das neue Set wirklich neu ist. |

## Annahmen (gelten, wenn du bei der Freigabe nichts anderes sagst)

- A1 Ausgewerteter Detektor: **rules-only** `myxguard.scan`, feste Schwelle **25** (wie `scripts/benchmark.py`). Keine Schwellen-Suche auf dem Test-Set. XLM-R nur als Zusatz, wenn du eine Python-Umgebung mit torch nennst.
- A2 Kategorien im Test-Set: `instruction_override`, `data_exfiltration`, `jailbreak_persona`, `benign`. Damit das Schema identisch bleibt (B7), gibt es kein neues Feld. Bei benign steht der Untertyp im bestehenden optionalen Feld `note`: `plain`, `roleplay` oder `hard_negative`. Der Scanner liest `note` nicht.
- A3 Ziel pro Sprache: je Angriffskategorie ≥ 15 Zeilen, benign ≥ 45 (davon ≥ 15 Rollenspiel-Bitten, ≥ 15 hard negatives). Tatsächliche Zahlen werden berichtet, auch wenn das Ziel verfehlt wird.
- A4 Per-Kategorie-Precision: Teilmenge = Zeilen der Kategorie + alle benign-Zeilen derselben Sprache (one-vs-benign). So definiert, weil ein Binär-Detektor keine Kategorie vorhersagt. Steht so im Bericht.
- A5 Leak-Zeilen werden **vor** der ersten Auswertung entfernt und gezählt. Nach der Auswertung wird das Set nicht mehr verändert.
- A6 Kein Text wird von Apertus erzeugt. Claude schreibt keine Test-Texte (siehe offene Frage).

## Schritte

Legende: **∥** = parallel ausführbar. Jeder Check ist vor der Arbeit festgelegt.

### S0 – Sicherung (Vorschlag)
- Output: Git-Commit-Vorschlag "harness: add HARNESS.md + plan.md" (nur lokal, kein Push). Nur auf dein OK.
- Liest: `git status`. Schreibt: nichts.
- Check: `git status` sauber nach Commit.

### S1 – CLAUDE.md anlegen
- Output: `CLAUDE.md` (Projektregeln aus HARNESS.md, erlaubte/verbotene Pfade, Liste aller Scripts/Tests, Regel-Log aus Layer 6).
- Liest: HARNESS.md, dieser Plan. Schreibt: `CLAUDE.md`.
- Check C1: Datei existiert; enthält jede `project_rule` aus HARNESS.md (Stichwortsuche per Script `scripts/check_claude_md.py`, 7/7 Treffer).

### S2 – Prüf-Tools zuerst (Layer 3)  ∥ S3/S4
- Output:
  - `scripts/check_schema.py` – jede Zeile in `datasets/test_fresh/*.jsonl` hat die Pflichtfelder von B7, gültige Werte für `label`/`language`/`category`, nicht-leeren `text`, `license` gesetzt. Exit≠0 bei Fehler.
  - `scripts/check_leakage.py` – nutzt `training.dedupe.NearDupIndex` (exakt, contain, jaccard ≥ 0.80, ratio ≥ 0.86). Sperrliste: `datasets/train`, `datasets/dev`, `datasets/eval`, `datasets/samples.jsonl`, `datasets/deepset_sample.jsonl`, `../apertus/test_fresh.jsonl`; bei XLM-R zusätzlich die apertus-Trainingsdateien. Prüft auch Duplikate innerhalb von test_fresh. Exit≠0 bei ≥ 1 Treffer; schreibt `reports/leakage_<datum>.json`.
  - `tests/test_fresh_tools.py` (neu) – synthetische Fälle: exakte Kopie, Ein-Wort-Änderung, Akzent-/Gross-Klein-Variante werden erkannt; fremder Satz nicht; fehlendes Feld / falsche Sprache wird vom Schema-Check abgelehnt.
- Liest: `training/dedupe.py`, je eine Zeile aus train/dev/eval. Schreibt: die drei Dateien.
- Check C2: `tests/test_fresh_tools.py` grün. **Blocker B5:** ohne pytest laufen die Testfunktionen per `python -c` als Fallback; "pytest grün" bleibt dann `unresolved`.

### S3 – Externe Quellen holen (blockiert bis Download-Freigabe)  ∥ S2/S4
- Output: `datasets/test_fresh/raw/<quelle>.jsonl` (Rohdaten, unverändert), `datasets/test_fresh/SOURCES.md` (URL, Revision/Datum, Lizenz laut Card, Zeilen genommen, Auswahlregel), `reports/third_party_notices_draft.md`.
- Kandidaten: `Lakera/gandalf_ignore_instructions` (EN, Angriffe; Lizenz beim Download aus der Card übernehmen). hackaprompt: nicht verwenden (B2). Weitere mehrsprachige Quellen nur nach deiner Freigabe pro Quelle.
- Auswahlregel vor dem Ansehen festgelegt: Zufallsstichprobe mit festem Seed (`seed=20261030`), keine Auswahl nach Detektor-Ergebnis.
- Check C3: jede Quelle in SOURCES.md hat Lizenz + URL; Lizenz ist mit Open Source vereinbar (MIT/Apache-2.0/CC-BY-*); sonst Quelle verwerfen.

### S4 – Handgeschriebene Zeilen (Platzhalter)  ∥ pro Sprache: S4-de ∥ S4-fr ∥ S4-it ∥ S4-en
- Output: `datasets/test_fresh/handwritten_<lang>.jsonl` – leere Vorlage mit Formatbeispiel in `datasets/test_fresh/README.md`; Inhalt kommt von Menschen (du/Bekannte/Muttersprachler). `source: "myxguard-fresh-handwritten"`, `license: "MIT"`.
- Check C4: Schema-Check grün; je Zelle Sprache×Kategorie Anzahl gegen A3 berichtet.

### S5 – Test-Set zusammenbauen
- Output: `scripts/build_test_fresh.py` → `datasets/test_fresh/test_fresh.jsonl` (+ `build_report.json` mit Zählungen pro Sprache×Kategorie×Quelle).
- Liest: `datasets/test_fresh/raw/*`, `handwritten_*`. Schreibt: die zwei Dateien.
- Check C5: `check_schema.py` Exit 0; Zählungen im build_report = Zeilen in der Datei; alle 4 Sprachen und 4 Kategorien vorhanden (sonst `fail` mit Zelle).

### S6 – Leakage-Check (Pflicht vor jeder Auswertung)
- Output: `reports/leakage_<datum>.json`; bei Treffern: Zeilen entfernt, Liste in `reports/leakage_removed_<datum>.jsonl`, dann S5/S6 erneut.
- Check C6: `check_leakage.py` meldet **0 Treffer** auf der gespeicherten `test_fresh.jsonl` (SHA-256 im Report).

### S7 – Auswertung pro Sprache  ∥ S7-de ∥ S7-fr ∥ S7-it ∥ S7-en
- Output: `scripts/eval_test_fresh.py --lang <xx>` → `reports/raw/eval_<lang>_<datum>.json`. Startet nur, wenn `leakage_<datum>.json` zur aktuellen SHA-256 passt und 0 Treffer zeigt.
- Inhalt: TP/FP/TN/FN, Precision, Recall, F1 pro Sprache und pro Kategorie (A4), FPR auf benign pro Sprache und pro `subtype`, Confusion Matrix, alle Fehlbeispiele (mind. 10 ausgegeben, falls es so viele gibt), Score pro Zeile.
- Check C7: JSON hat alle Pflichtfelder; Zahlen konsistent (TP+FN = #malicious, FP+TN = #benign); Fehlbeispiele ≥ 10 **oder** Anzahl Fehler < 10 (dann `unresolved` mit Grund, Set wird nicht angepasst).

### S8 – Bericht zusammenführen
- Output: `reports/eval_<datum>.md` – Tabellen pro Sprache, pro Kategorie, FPR, Confusion Matrices, Fehlbeispiele, Methode (Detektor, Schwelle, Seed, SHA-256 des Sets, Quellen+Lizenzen), Grenzen (kleine n, Konfidenzintervall Wilson 95 % pro Rate).
- Check C8: jede Zahl im Bericht stammt aus `reports/raw/*.json` (Script `scripts/check_report_numbers.py` vergleicht).

### S9 – Abschluss
- Output: `checks.md` (Schritt | Anforderung | Urteil | Beleg), `progress.md`, `reports/devlog_draft.md` (Entwurf, nicht in DEVLOG.md eingetragen, Status "v0.1, Frühphase").
- Check C9: gesamte pytest-Suite grün (bestehende + neue Tests) – abhängig von B5; jeder Output in Layer 7 öffnet sich; CLAUDE.md enthält jede neue Regel.

## Abhängigkeiten

S1 → S2 ∥ S3 ∥ S4 → S5 → S6 → S7 (4× ∥) → S8 → S9.
S3 ist blockiert bis Download-Freigabe; S4 blockiert bis handgeschriebene Zeilen da sind. S2 und S1 können sofort laufen.

## Freigaben, die ich brauche

1. Plan freigeben (oder Annahmen A1–A6 korrigieren).
2. S0-Commit ja/nein.
3. Download `Lakera/gandalf_ignore_instructions` (Hugging Face, Grösse nenne ich vor dem Download).
4. `pip install pytest` (Download) – sonst bleibt der pytest-Check `unresolved`.

## Offene Frage (eine) – beantwortet: (a)

Gandalf liefert nur Englisch, hackaprompt ist schon im Training. **Wer schreibt die de/fr/it-Texte (Angriffe und harmlose)?**
(a) du/Muttersprachler schreiben sie von Hand, ich baue nur Vorlage + Tools; (b) Claude entwirft sie und du prüfst jede Zeile – dann wäre das Set modell-erzeugt und das stünde so im Bericht; (c) nur englische externe Daten jetzt, de/fr/it bleiben `unresolved`.
