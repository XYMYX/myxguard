<prompt>

<inputs>
Projekt: myxguard – mehrsprachiger Prompt-Injection-Detektor (en/de/fr/it), Open Source.
Aufgabe: Frisches Test-Set mit neuen Formulierungen aufbauen (Angriffe UND harmlose Texte, alle vier Sprachen)
  und myxguard pro Sprache dagegen auswerten. Quellen: externe, NICHT im Training verwendete Daten
  (z. B. Lakera/gandalf_ignore_instructions, hackaprompt) plus Platz für von Hand geschriebene Beispiele.
  Nichts davon von Apertus generieren lassen.
Ergebnis und Ausgabepfad: datasets/test_fresh/ (JSONL) + reports/eval_<datum>.md
Quellmaterial: das ganze Repo – zuerst README.md, DEVLOG.md, training/README.md, datasets/, training/dedupe.py, tests/.
Erlaubte Änderungen: datasets/test_fresh/, reports/, scripts/, tests/ (nur neue Tests), plan.md, checks.md, progress.md, CLAUDE.md.
  NICHT ändern: datasets/train, datasets/dev, datasets/eval, training/, myxguard/ (Detektor-Code).
Limit: max. 3 Korrekturversuche pro Schritt. Kein Training, kein Push, kein Download ohne meine Freigabe.

Fehlt ein Detail, das das Ergebnis verändert: genau eine gezielte Frage stellen.
</inputs>

<goal>
Erledige die Aufgabe als Harness, nicht als langen Chat.
Liefere: Ergebnis, Prüfbericht (checks.md), CLAUDE.md (neu anlegen, falls nicht vorhanden).
Stoppe, wenn alle Checks bestanden sind oder das Limit erreicht ist.
</goal>

<project_rules>
- Kategorien: instruction_override, data_exfiltration, jailbreak_persona, benign.
- Alle vier Sprachen (en, de, fr, it) einzeln auswerten, nie nur ein Gesamtwert.
- Harmlose Rollenspiel-Bitten (z. B. «Spiel einen strengen Coach») sind benign und dürfen nicht geblockt werden.
- Test-Daten dürfen nie in train/dev/eval vorkommen – auch nicht leicht umformuliert. training/dedupe.py wiederverwenden, wenn passend.
- Fehlalarme auf harmlosen Texten sind genauso wichtig wie erkannte Angriffe.
- Alle Zahlen berichten, auch die schlechten. Nichts schönrechnen.
- Lizenz jeder externen Quelle notieren (THIRD_PARTY_NOTICES.md beachten), weil das Projekt Open Source ist.
</project_rules>

<role>
Du bist der Lead dieses Harness.
- Lies zuerst CLAUDE.md (falls vorhanden) und den Repo-Stand, bevor du etwas änderst.
- Planen und Zusammenführen machst du selbst; abgegrenzte Teilaufgaben gehen an Subagents.
- Halte jede Entscheidung fest, die den Harness verändert.
</role>

<layer_1_plan>
Wechsle vor jeder Änderung in den Plan-Modus. Plan als Schritte mit je einem Output und einem Check.
- Pro Schritt: welche Dateien gelesen und geschrieben werden.
- Parallele Schritte markieren (z. B. Auswertung pro Sprache).
- Checks VOR der Arbeit schreiben.
Speichere den Plan in plan.md und warte auf meine Freigabe.
</layer_1_plan>

<layer_2_context>
- Pro Schritt nur CLAUDE.md und die genannten Dateien laden.
- Subagents bekommen nur: Schritt, Inputs, Check.
- Lange Logs und Rohausgaben bleiben aus der Hauptsession draussen; nur Pfad, Urteil, Beleg zurückmelden.
</layer_2_context>

<layer_3_tools_hooks>
Feste Regeln werden Scripts oder Tests, keine Anweisungen:
- Leakage-Check: exakte und fast-identische Texte zwischen test_fresh und train/dev/eval. Muss vor jeder Auswertung laufen.
- Schema-Check: jede JSONL-Zeile hat dieselben Felder wie die bestehenden Datensätze.
- Bestehende Tests (pytest) müssen weiterhin grün sein.
Liste jedes Script und jeden Test in CLAUDE.md auf.
Fehlt ein Tool oder Netzwerk: Blocker benennen, restliche Schritte weiterführen.
</layer_3_tools_hooks>

<layer_4_permissions>
- Änderungen nur in den erlaubten Pfaden.
- Kein Training, kein git push, kein Download ohne meine ausdrückliche Freigabe.
- Vor riskanten Änderungen einen Git-Commit als Sicherung vorschlagen.
- Nie zwei Sessions an derselben Datei.
</layer_4_permissions>

<layer_5_verification>
Jeder Schritt muss sich mit echten Signalen beweisen: Script-Ausgabe, Metriken, Tests. Deine Zuversicht zählt zuletzt.
checks.md mit einer Zeile pro Anforderung:
Schritt | Anforderung | Urteil | Beleg
Urteil: pass, fail oder unresolved. Fehlende Belege bleiben sichtbar.

Pflicht-Checks für die Auswertung:
- Precision, Recall, F1 pro Sprache und pro Kategorie.
- Fehlalarm-Rate auf harmlosen Texten pro Sprache.
- Confusion Matrix.
- Leakage-Check bestanden (0 Treffer).
- Mindestens 10 Fehlbeispiele pro Sprache zum Anschauen.
</layer_5_verification>

<layer_6_feedback>
Korrektur: Fehlgeschlagener Check → Schritt zurück mit Grund, Beleg und "nur diesen Schritt fixen". Max. drei Versuche.
Gedächtnis: Fehler oder Korrektur → Regel in CLAUDE.md, damit es nicht wieder passiert.
</layer_6_feedback>

<layer_7_completion>
Abschluss-Checkliste, jeder Punkt mit Beleg:
- Jeder Output existiert und lässt sich öffnen.
- Jeder Check lief gegen die gespeicherte Version.
- Fehler sind behoben oder ausdrücklich gemeldet.
- CLAUDE.md enthält jede neue Regel.
Stoppt ein Limit oder Blocker: Teilstatus mit den genauen offenen Schritten.
</layer_7_completion>

<execution_loop>
1. plan.md lesen, nächste bereite Schritte wählen.
2. Unabhängige Schritte parallel.
3. Jeden Output gegen seinen Check prüfen.
4. Nur fehlgeschlagene Schritte zurückgeben.
5. Akzeptierte Outputs zusammenführen, alle Checks laufen lassen.
6. Weiter bis Abschluss, Blocker oder Limit.
Schwäche nie einen Check ab und passe nie das Test-Set an, nur um bessere Zahlen zu bekommen.
</execution_loop>

<handoff>
Nach jeder Etappe progress.md aktualisieren:
Plan (erledigt / läuft / blockiert), Outputs (exakte Pfade), Entscheidungen (was und warum), offene Punkte, nächste Aktion.
Beim Wiederaufnehmen zuerst CLAUDE.md, plan.md und progress.md lesen.
</handoff>

<delivery>
Gib zurück: datasets/test_fresh/, reports/eval_<datum>.md, plan.md, checks.md, progress.md, Diff von CLAUDE.md.
Dazu ein Entwurf für DEVLOG.md (nicht selbst eintragen): alle Zahlen pro Sprache, auch die schlechten, Status "v0.1, Frühphase".
Sag klar, was geprüft wurde, was bestanden hat und was offen bleibt.
Verbrauch nur nennen, wenn gemessen.
</delivery>

</prompt>
