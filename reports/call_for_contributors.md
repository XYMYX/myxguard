# MyxGuard: looking for French and Italian native speakers

**MyxGuard** is an open-source prompt-injection detector for **German, French, Italian and English** (MIT license). Most existing tools only work well in English. MyxGuard is meant to close that gap for anyone who wants to protect their own chatbot.

## Where the project stands (v0.1, early stage)

I built a new test set with 609 texts in four languages, checked so that none of them appear in the training data. Results per language:

| Language | Rules: attacks caught | XLM-R model: attacks caught | XLM-R: harmless texts blocked |
|---|---:|---:|---:|
| German | 1 % | 71 % | 6 % |
| English | 16 % | 85 % | 10 % |
| French | 1 % | 63 % | 6 % |
| Italian | 0 % | 61 % | 6 % |

- The keyword rules almost never catch new wording.
- The multilingual classifier does much better, but it is not yet usable as a real defence. It misses most data-exfiltration attempts and wrongly blocks some harmless role-play requests ("play a strict coach").
- French and Italian are the weakest languages, and **so far no native speaker has written or checked the French and Italian texts**. That is the main problem I need help with.

Full report and method: `reports/eval_2026-10-30.md`.

## What I am looking for

**Native speakers of French or Italian** (Swiss variants welcome) who can write short test texts by hand. About 90 lines per person is ideal, but any number helps:

- **Attacks (15 each):** texts that try to make a chatbot ignore its instructions, leak data or secrets, or play an "unrestricted" persona.
- **Harmless texts (45):** everyday requests (20), harmless role-play requests (10–15), and tricky but harmless texts (15), for example a question that quotes an attack or "ignore the footnotes".

Rules:

- Write it yourself. Please **no AI-generated text** and no translations of existing datasets.
- Use new ideas and your natural way of writing.
- The texts are **only used for testing**, never for training, and are released under MIT with credit to you (or anonymously, if you prefer).

Format: one line per text, `language|label|category|text`. Details are in `datasets/test_fresh/README.md`.

## How to help

Open an issue or a pull request, or contact me via GitHub. Questions are welcome too.

Thank you! 🙏

---

**FR:** Vous parlez français ? J'ai besoin de textes de test écrits à la main pour un détecteur open source. Toute aide compte.
**IT:** Parli italiano? Cerco testi di prova scritti a mano per un rilevatore open source. Ogni aiuto conta.
