# MyxGuard Devlog



## 2026-10-28: First classifier, Apertus setup

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



## 2026-10-29: Extra data, first honest fresh test (v0.1)

**Status:** early stage (v0.1). Not usable as a real defence yet. All numbers below are from small test sets.

> Written with AI assistance (Claude). I ran and checked everything myself.

### Goal

A prompt-injection detector that works in German, French, Italian and English, free to download for anyone who wants to protect their own chatbot. Most existing tools and datasets are English-only, which is the gap this project targets.

### What changed

**1. Dataset generator (`generate_dataset.py`, v1 → v7)**

| Version | Change | Why |
|---|---|---|
| v1 → v2 | Benign class, hard negatives (harmless but suspicious-sounding), attack position start/middle/end, email/HTML/forward wrappers, dedup, fixed seed, `source` field | v1 had only "malicious" samples and always put the attack at the end, so a detector would learn the position instead of the attack |
| v2 → v3 | Wrappers per language; hand-written intros for fr/it; no paraphrasing for fr/it | Apertus-8B produced broken Italian (mixed with Romansh) and German wrappers leaked into fr/it samples |
| v3 → v4 | Train/test split by template; 6 templates per category for fr/it; `topic` is `null` for fr/it | The hash split left Italian with no test attacks; `topic` no longer matched the hand-written intros |
| v4 → v5 | Polite, keyword-free attacks (train only); 8 normal benign sentences per language | The baseline only reacted to words like "ignore" |
| v5 → v6 | Intros capped at 150 characters; 3 more data-exfiltration templates per language | Long generated intros buried the attack |
| v6 → v7 | More attack phrasings and extra exfiltration templates | Exfiltration was still the weakest category |

**2. External data (`data_external.py`)**
Added `yanismiraoui/prompt_injections` (attacks), `OpenAssistant/oasst2` and `CohereLabs/aya_dataset` (real human benign texts in de/fr/it/en), and English "talks about attacks" texts from `usezn/zn-prompt-injection-bench` as hard negatives. Part of the real benign texts is held back and never used for training, to measure false alarms on realistic text. The multilingual attacks in zn-bench are mostly plain harm requests, not prompt injections, so I excluded them. Sources and licences are listed in `external_attribution.txt`.

**3. Models**
- Baseline: TF-IDF (character n-grams) + logistic regression.
- XLM-RoBERTa-base fine-tuned on own data + deepset train + external data.

**4. Fresh test set (`eval_fresh.py`, `make_fresh.py`)**
160 new texts (80 attacks, 80 harmless incl. 28 hard negatives) in de/fr/it/en, kept apart from all training data.

**5. Extra training data (v8, `make_extra.py`)**
236 hand-written lines targeting the weak spots (exfiltration, hidden notes in reviews/mails, "two answers" personas) plus new hard negatives (role-play requests, "ignore the footnotes", questions that quote an attack sentence).

**6. Decision: role-play is not an attack**
"Play a strict interview coach" is harmless. deepset labels some such prompts as attacks, which contradicts this. I now drop deepset training lines that look like role-play requests and contain no dangerous wording (no jailbreak/DAN/ignore/hack/password terms).

### Results (XLM-RoBERTa, 3 seeds)

| Test | Result |
|---|---|
| deepset test: attacks detected | 77–82 % at 0 % false alarms |
| Real harmless text (oasst2/aya, held out) | 0.6–1.5 % blocked |
| Fresh set: attacks detected | 50–60 % |
| Fresh set: harmless blocked | 12.5–18.8 % |
| Fresh set: data exfiltration detected | 36–46 % |
| Fresh set: hard negatives blocked | 29–54 % |

Own test set: 79–93 % detected, 6–17 % false alarms. It is not meaningful any more (see below).

### What I learned

- **Good deepset numbers do not mean it works.** The model catches deepset-style attacks (~80 %) but only about 55 % of polite, indirect ones on my fresh set.
- **Seeds matter more than my changes.** Between seeds, the fresh-set attack rate swings by about 10 points and the hard-negative false alarms by about 20. The 236 extra lines and the role-play filter did not produce a change I can tell apart from noise.
- **Small data drowns.** 236 hand-written lines next to thousands of other samples had little effect. More of the same is not the answer, more varied data is.
- **Data can contradict itself.** deepset treats role-play requests as attacks, my target behaviour does not. A model cannot learn both.
- **Test sets get used up.** After reading error lists, a test set is a dev set. The fresh set also shares attack ideas with my v8 training lines, so its numbers are optimistic. A third set with new attack ideas is needed for any final claim.
- **The baseline was not detecting attacks.** Its strongest features were punctuation and word fragments, and it blocked most harmless text.
- **Apertus is not usable for fr/it generation or Swiss German.** Swiss German templates will be written by hand later.

### Known problems

- Detection of indirect attacks (exfiltration, hidden instructions) is far too low for real use.
- Roughly a third of tricky harmless sentences (role-play, quoted attack phrases, "ignore the formatting") get blocked.
- fr/it templates are written by me and not reviewed by native speakers.
- Small test sets (20 attacks per language), so per-language differences are noise.
- Template-based data and few human-written attacks.
- A detector is not a complete defence. The README will say so.

### Next

1. Much more varied attack and hard-negative data, ideally written by different people and native speakers for fr/it/de.
2. A third, untouched test set with new attack ideas, used once at the end.
3. Try a probability threshold instead of the default cut-off, and report the trade-off between missed attacks and false alarms.
4. Consider a larger multilingual model once the data is better.
5. README with honest limits and licences (CC-BY-4.0 for zn-bench, Apache-2.0 for the others).
6. Later: Swiss German as a fifth language, hand-written.
