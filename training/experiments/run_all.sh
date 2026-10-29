#!/bin/bash
# Alles in einem Rutsch: Zusatzdaten bauen, 3 Seeds trainieren, jeweils auf test_fresh.jsonl auswerten.
# Aufruf (Git Bash, im Projektordner, .venv aktiv):  bash run_all.sh
# Logs: log_train_<seed>.txt und log_fresh_<seed>.txt
export EXTRA_REPEAT=${1:-1}   # bash run_all.sh 5  -> Zusatzdaten 5x
echo "Zusatzdaten x$EXTRA_REPEAT"
python make_extra.py
for s in 1 2 3; do
  echo "=== Seed $s ==="
  python train_xlmr.py $s 1.0 > log_train_$s.txt 2>&1 || { echo "Training Seed $s fehlgeschlagen, siehe log_train_$s.txt"; tail -n 15 log_train_$s.txt; exit 1; }
  python eval_fresh.py > log_fresh_$s.txt 2>&1 || { echo "Auswertung Seed $s fehlgeschlagen, siehe log_fresh_$s.txt"; tail -n 15 log_fresh_$s.txt; exit 1; }
  grep ERGEBNIS log_train_$s.txt
  grep -a -E "Texte aus|^  alle|data_exfiltration  |hard_negative  |jailbreak_persona  |instruction_override  " log_fresh_$s.txt
done
echo "Fertig. Kopier mir einfach alles ab '=== Seed 1 ==='."
