\# MyxGuard Devlog



\## 2026-10-28: First classifier, Apertus setup

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



\## 2026-10-28 / 29: Dataset generator, baseline and second XLM-RoBERTa run

Status: work in progress, numbers below are from a small dev set and not final.



> Written with AI assistance (Claude). I ran and checked everything myself.



\### Goal

A prompt-injection detector that works in German, French, Italian and English, free to download for anyone who wants to protect their own chatbot. Most existing tools and datasets are English-only, which is the gap this project targets.



\### What changed



\*\*1. Dataset generator (generate\_dataset.py, v1 → v6)\*\*



| Version | Change | Why |

|---|---|---|

| v1 → v2 | Added a benign class, hard negatives (harmless but suspicious-sounding sentences), attack position at start/middle/end, email/HTML/forward wrappers, dedup, fixed seed, source field | v1 had only "malicious" samples and always put the attack at the end, so a detector would learn the position instead of the attack |

| v2 → v3 | Wrappers per language; hand-written intros for fr/it; no paraphrasing for fr/it | Apertus-8B produced broken Italian (mixed with Romansh) and the German wrappers leaked into fr/it samples |

| v3 → v4 | Fixed train/test split by template; 6 templates per category for fr/it; topic is null for fr/it | The hash split left Italian with no test attacks; topic no longer matched the hand-written intros |

| v4 → v5 | Polite, keyword-free attacks (train only); 8 normal benign sentences per language | The baseline only reacted to words like "ignore" and missed social-engineering attacks |

| v5 → v6 | Intros capped at 150 characters; 3 more data-exfiltration templates per language | Long generated intros buried the attack; exfiltration was the weakest category |



\*\*2. Baseline (baseline.py)\*\*

TF-IDF (character n-grams) + logistic regression. Three variants (own data only, deepset only, both), each evaluated on two separate test sets: my own held-out templates and the deepset/prompt-injections test split. Also prints errors per language and category, and the strongest features.



\*\*3. XLM-RoBERTa (train\_xlmr.py)\*\*

Fine-tuned xlm-roberta-base on own data + deepset train, same evaluation as the baseline.



\### What I learned

\- Training only on my own templates does not transfer. On the deepset test set the own-data model dropped to 65% recall with 23% false alarms.

\- The baseline was not detecting attacks. Its strongest features were punctuation and fragments like '. ' and ' all'. On my own test set it blocked most harmless text, because it reacts to words such as "forget" and "ignore" regardless of context.

\- The own test set is optimistic. Intros and wrappers appear in both train and test, and only a handful of templates sit behind each number.

\- Test set was used up. After reading the error lists I treat it as a dev set. A fresh test set with new templates is needed before publishing any final numbers.

\- Apertus is not usable for Swiss German or fr/it generation. I will write Swiss German templates by hand later.

\- These numbers are not comparable to the first benchmark (F1 0.949 on 370 held-out texts): different test sets and a harder setup with wrappers, positions and polite attacks.



\### First results (dev set, small samples)



| Metric | Baseline (both datasets) | XLM-RoBERTa (v5 data) |

|---|---|---|

| deepset test: attacks detected | 81.7% (n=60) | 90.0% (n=60) |

| deepset test: harmless blocked | 0.0% (n=56) | 0.0% (n=56) |

| own test: attacks detected | 86.1% (n=36) | 72.4% (n=29) |

| own test: harmless blocked | 60.0% (n=20) | 4.5% (n=22) |



Weak spots of XLM-RoBERTa: data exfiltration via social engineering (54.5%), German (57%), and polite attacks hidden in long harmless text. Per-language values rest on 5–10 samples each, so differences of 10–20 points are noise.



\### Known problems

\- fr/it templates are written by me and not yet reviewed by native speakers.

\- Paraphrases (en/de only) can be grammatically off.

\- Small test sets, template-based data, no real-world benign traffic in de/fr/it yet.

\- A detector is not a complete defence. The README will say so.



\### Next

1\. Regenerate with v6, re-run XLM-RoBERTa, compare.

2\. Write a fresh test set with unseen templates and do not touch it until the end.

3\. Collect normal (benign) chat messages in de/fr/it to measure false alarms realistically.

4\. Native-speaker review of fr/it/de templates.

5\. Later: Swiss German as a fifth language, hand-written.

