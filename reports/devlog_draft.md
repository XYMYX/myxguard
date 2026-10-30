# Draft for DEVLOG.md (not added – please review and paste yourself)

## 2026-10-30: Third fresh test set, rules and XLM-R (v0.1)

**Status:** early stage (v0.1). Not usable as a real defence. All numbers below are from one run on a small test set.

> Written with AI assistance (Claude). Test texts were written by me; the Gandalf rows are from Lakera (MIT).

### What I did

- Built a new fresh test set `datasets/test_fresh/test_fresh.jsonl` (609 rows): 559 hand-written rows in de/fr/it/en plus 50 English attacks sampled from `Lakera/gandalf_ignore_instructions` (MIT, seed 20261030).
- Added a leakage check (`scripts/check_leakage.py`, reuses `training/dedupe.py`) against train, dev, eval, samples, deepset_sample and the old fresh set. It must pass before any evaluation, and the evaluation script refuses to run otherwise.
- The check removed 161 of my 720 hand-written lines before scoring: 160 were exact copies of the old, used-up fresh set and 1 was a near-duplicate of a training row. Final set: 0 leaks.
- Evaluated the rules-only detector (`myxguard.scan`, threshold 25, not tuned) once, per language.

### Results (rules only, threshold 25)

| Language | Attacks detected | Harmless blocked |
|---|---|---|
| de | 1 / 70 (1.4 %) | 1 / 70 (1.4 %) |
| en | 19 / 119 (16.0 %), of which Gandalf 15 / 50, hand-written 4 / 69 | 0 / 70 |
| fr | 1 / 70 (1.4 %) | 0 / 70 |
| it | 0 / 70 (0.0 %) | 0 / 70 |

- Data exfiltration: 0 detected in every language (0 / 23 each).
- Role-play requests: 0 blocked (11 in de, 12 each in en/fr/it, too few to say much).
- The single false alarm is a German question that quotes a "you are DAN now" line.
- Sanity check: the same pipeline gives recall 0.425 with 0 false alarms on the old held-out set, identical to `scripts/benchmark.py`. So the collapse comes from the new wording, not from a bug.

### XLM-R classifier on the same set (same day, model unchanged, argmax)

| Language | Attacks detected | Harmless blocked | Role-play blocked | Exfiltration detected |
|---|---|---|---|---|
| de | 50 / 70 (71.4 %) | 4 / 70 (5.7 %) | 2 / 11 | 9 / 23 |
| en | 101 / 119 (84.9 %), of which Gandalf 50 / 50, hand-written 51 / 69 | 7 / 70 (10.0 %) | 3 / 12 | 10 / 23 |
| fr | 44 / 70 (62.9 %) | 4 / 70 (5.7 %) | 1 / 12 | 9 / 23 |
| it | 43 / 70 (61.4 %) | 4 / 70 (5.7 %) | 1 / 12 | 7 / 23 |

- Far better than the rules, but it blocks harmless text, including 7 of 47 role-play requests. That breaks my own rule that role-play is harmless.
- Exfiltration is still the weakest category (7–10 of 23).
- Sanity check: on the old fresh set this model gives 47/80 attacks detected and 15/80 harmless blocked, inside my earlier 3-seed range.
- Leakage check covered all data this model was trained on: 0 hits. The training log proves the v8 extra lines were not in it (see correction below).
- Only one saved model (seed 3). Seeds swung by about 10 points before.

### What I learned

- **The rules only know the phrasings they were written for.** On new wording, 66–68 of 70 attacks per language in de/fr/it get score 0: no rule fires at all. Indirect instructions inside emails, recipes or calendar invites, personas without words like "DAN", exfiltration through URLs and tools, and casual overrides all pass.
- **Few false alarms mean nothing here.** The detector barely fires, so of course it rarely fires wrongly.
- **Even classic "ignore your instructions" is weak:** 15 of 50 Gandalf prompts detected; 9 of the misses reach score 10, below the threshold.
- **Check that extra data actually reaches training.** `make_extra.py` was empty, even in git, so `extra_train.jsonl` was never created. `train_xlmr.py` silently treats a missing file as empty. The log line "Zusatzdaten x5" looked fine, but 5 × 0 lines were added.
- **Check new data against old test sets first.** Almost half my first batch was the old fresh set copied over. Without the leakage check the numbers would have been inflated by a used-up set.

### Known problems

- XLM-R: one seed only.
- XLM-R blocks harmless role-play requests (7 of 47).
- Role-play target (15 per language) missed: 11–12.
- Many role-play attacks share the same idea across the four languages: fairer language comparison, less variety.
- fr/it texts are not reviewed by native speakers.
- This set is now used up (I have seen the errors). Any future claim needs another untouched set.

### Next

1. Treat this set as a dev set from now on.
2. Rules alone will not cover indirect and polite attacks; the classifier is the main path.
3. Classifier: more role-play hard negatives and more exfiltration attacks in training, then a new untouched test set.
4. Recreate the v8 lines (the script is gone) or drop the claim. Make `train_xlmr.py` fail on a missing data file instead of silently skipping it.

### Correction to the 2026-10-29 entry

The 236 v8 lines (`make_extra.py`) were never in training: the script is empty (also in git, commit `9b3faea`), so `extra_train.jsonl` was never written. `train_xlmr.py` skips a missing file without an error. All three seed logs show 2183 external rows, which is exactly `external_train.jsonl`, and 154 + 546 + 2183 = 2883 training rows. The statement "the 236 extra lines … did not produce a change I can tell apart from noise" is therefore not supported. The lines were not tested at all.
