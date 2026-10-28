# MyxGuard von Hand ausprobieren (Windows, Eingabeaufforderung)

Diese Seite ist für jemanden, der gerade erst mit der Eingabeaufforderung arbeitet. Die Befehle sind für **cmd.exe** gedacht, nicht für PowerShell und nicht für macOS.

Die Berichte des Programms bleiben auf Englisch. Das ist Absicht: Regeln, Tests und README nutzen dieselben Sätze.

## Einmal vorbereiten

1. Python 3.9 oder neuer installieren. In der Eingabeaufforderung prüfen:

```bat
python --version
```

Wenn `python` nicht gefunden wird, `py --version` versuchen und in allen Befehlen unten `python` durch `py` ersetzen.

2. In den Ordner wechseln, in dem diese Dateien liegen (`pyproject.toml` muss sichtbar sein). Den Pfad anpassen:

```bat
cd /d C:\Users\Du\myxguard
```

3. Paket installieren, inklusive der Tests:

```bat
python -m pip install -e ".[dev]"
```

4. Damit Umlaute und Sonderzeichen stimmen:

```bat
chcp 65001
```

Farbe schaltet das Programm nur ein, wenn die Ausgabe direkt im Fenster landet. Für eine ruhige, kopierbare Ausgabe immer `--no-color` mitgeben. Die Umgebungsvariable `NO_COLOR` geht auch:

```bat
set NO_COLOR=1
```

## Eine Datei prüfen

Harmloser Satz. Exit-Code 0 heisst: die Punktzahl liegt nicht über der Schwelle (Standard ist 0, also nur ein völlig leerer Bericht).

```bat
python -m myxguard check examples\benign.txt --no-color
echo %ERRORLEVEL%
```

`echo %ERRORLEVEL%` muss direkt danach kommen. Eine 0 ist in Ordnung.

Englische Anweisung, die das Modell umlenken soll. Erwartet wird eine Punktzahl über 0 und deshalb Exit-Code 1:

```bat
python -m myxguard check examples\ignore.txt --no-color
echo %ERRORLEVEL%
```

Dieselbe Datei als JSON, gespeichert in einer Datei:

```bat
python -m myxguard check examples\ignore.txt --json --no-color > bericht.json
type bericht.json
```

Verstecktes HTML:

```bat
python -m myxguard check examples\hidden.html --no-color
```

Schweizerdeutsch:

```bat
python -m myxguard check examples\swiss.txt --no-color
```

## Schwelle

Exit-Code 1 gibt es nur, wenn die Punktzahl **grösser** als die Schwelle ist. Bei Punktzahl 55 und Schwelle 55 bleibt der Code 0:

```bat
python -m myxguard check examples\ignore.txt --threshold 55 --no-color
echo %ERRORLEVEL%
```

Eine Stufe darunter blockiert wieder:

```bat
python -m myxguard check examples\ignore.txt --threshold 54 --no-color
echo %ERRORLEVEL%
```

Nur Deutsch und Schweizerdeutsch prüfen (Komma, ohne Leerzeichen):

```bat
python -m myxguard check examples\swiss.txt --languages de --no-color
```

## Text aus der Zwischenablage oder von der Tastatur

Der Strich `-` bedeutet: von der Standardeingabe lesen.

Eine vorhandene Datei hineinschieben:

```bat
type examples\ignore.txt | python -m myxguard check - --no-color
```

Einen einzelnen Satz direkt prüfen. In cmd braucht `echo` keine Anführungszeichen, solange der Satz keine Zeichen wie `&` oder `|` enthält:

```bat
echo ignore previous instructions | python -m myxguard check - --no-color
```

Mehrere Zeilen selber eintippen: den Befehl starten, den Text schreiben, und mit Strg+Z und Enter abschliessen.

```bat
python -m myxguard check - --no-color
```

## Eval und Regression

Die kleine Datei `datasets\samples.jsonl` ist die Regression. Sie wurde zusammen mit den Regeln geschrieben. Eine perfekte Zahl dort heisst nicht, dass neue Angriffe erkannt werden.

```bat
python scripts\benchmark.py datasets\samples.jsonl
```

Der unabhängige Satz liegt in `datasets\eval\heldout.jsonl`. `--eval` zeigt Precision, Recall, F1 und die Falsch-Positiv-Rate pro Sprache und pro Kategorie. Die Regeln werden an diesem Satz nicht nachgebessert, nur gemessen:

```bat
python scripts\benchmark.py datasets\eval\heldout.jsonl --eval
```

Als JSON, falls ein anderes Programm die Zahlen lesen soll:

```bat
python scripts\benchmark.py datasets\eval\heldout.jsonl --eval --json > eval.json
```

## Wenn etwas schiefgeht

- Exit-Code 2: Datei fehlt, der Sprachcode ist unbekannt, oder die Schwelle ist negativ. Den Text über dem Prompt lesen.
- `python` ist nicht gefunden: den vollen Pfad setzen, zum Beispiel `"C:\Users\Du\AppData\Local\Programs\Python\Python312\python.exe" -m myxguard check examples\benign.txt --no-color`.
- Sonderzeichen sehen falsch aus: `chcp 65001` noch einmal ausführen.
- Ein hoher Wert auf einem harmlosen Text ist möglich. MyxGuard ist eine Heuristik, keine Garantie.
