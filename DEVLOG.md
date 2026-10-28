\# MyxGuard Devlog



\## 2026-10-28

\*\*Done\*\*

\- Fixed ONNX export bug after GPU training (model moved to CPU before export)

\- Trained first xlm-roberta-base classifier locally on RTX 5090

\- Evaluated on 370 held-out texts: precision 0.947, recall 0.952, F1 0.949, FPR 0.054 (rules only: recall 0.425)

\- Added benchmark section (v0.1) to README

\- Set up Apertus 8B locally with my own Transformers launcher (chat.py)

\- Wrote generator, review and attack-template scripts (generate.py, review.py, clean.py, attack\_gen.py, check\_heldout.py)

\- Hand-reviewed generated texts, 227 new examples, 0 overlap with held-out set

\- Created separate repo myxguard-datagen for data-generation scripts



\*\*Learned\*\*

\- Small generator models write good benign hard negatives but weak attacks, so attacks are built from templates

\- Never train on the held-out set and always check for overlap



\*\*Next\*\*

\- Expand attack templates to 10–20 per language and category

\- Convert apertus\_batch1.jsonl to MyxGuard dataset format

\- Retrain and re-benchmark

