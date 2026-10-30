# Draft for DEVLOG.md (not added – please review and paste yourself)

## 2026-10-30: Third fresh test set, rules only (v0.1)

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

### What I learned

- **The rules only know the phrasings they were written for.** On new wording, 66–68 of 70 attacks per language in de/fr/it get score 0: no rule fires at all. Indirect instructions inside emails, recipes or calendar invites, personas without words like "DAN", exfiltration through URLs and tools, and casual overrides all pass.
- **Few false alarms mean nothing here.** The detector barely fires, so of course it rarely fires wrongly.
- **Even classic "ignore your instructions" is weak:** 15 of 50 Gandalf prompts detected; 9 of the misses reach score 10, below the threshold.
- **Check new data against old test sets first.** Almost half my first batch was the old fresh set copied over. Without the leakage check the numbers would have been inflated by a used-up set.

### Known problems

- Rules only. The XLM-R model was not evaluated in this run.
- Role-play target (15 per language) missed: 11–12.
- Many role-play attacks share the same idea across the four languages: fairer language comparison, less variety.
- fr/it texts are not reviewed by native speakers.
- This set is now used up (I have seen the errors). Any future claim needs another untouched set.

### Next

1. Evaluate the XLM-R classifier on this set too (needs a torch environment). It should be run before anyone tunes rules on these errors.
2. Treat this set as a dev set from now on.
3. Rules alone will not cover indirect and polite attacks; the classifier is the main path.
