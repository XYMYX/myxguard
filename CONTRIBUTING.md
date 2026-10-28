# Contributing to MyxGuard

MyxGuard is a small scanner on purpose. A change should stay readable by someone who is still learning Python. Explain *why* in a short comment when a check is not obvious. Do not add a runtime dependency. Python 3.9 is the oldest version we run.

Imports stay at the top of the file. The tests and the CLI must keep working on 3.9, so do not use syntax from newer Python (no `match` statements).

## Do not tune on the eval set

`datasets/eval/heldout.jsonl` is held out. Do not add, delete, or rewrite rows so the `--eval` score goes up, and do not change a regular expression because of a miss you only saw there. New examples that lock in a rule belong in `datasets/samples.jsonl`. Wording you want to tune against belongs in `datasets/dev/dev.jsonl`, which is original text and is allowed to change. Report eval numbers before and after a rule change, with `python scripts/benchmark.py datasets/eval/heldout.jsonl --eval`.

## Add a language

1. Copy `myxguard/data/patterns/it.json` to a new file, for example `es.json`. The file name does not select the language. The `_meta.language` field does.
2. Set `_meta.language` to a short lowercase code (`es`). Set `_meta.name` to the human name. If you adapted expressions from another project, fill `_meta.adapted_from` and add the same note to [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). Original rules use `"adapted_from": []`.
3. Give every pattern an id shaped like `lang.category.short_name`, for example `es.instruction_override.ignore_previous`. Ids must be unique across all packs.
4. Each pattern needs these fields:

   | Field | Meaning |
   | --- | --- |
   | `id` | Stable id, as above |
   | `category` | One of the names in the list below |
   | `severity` | `low`, `medium`, `high`, or `critical` |
   | `regex` | A Python regular expression |
   | `explanation` | One sentence a person can read. English, like the other packs |
   | `example` | A string the regex must match |
   | `benign_example` | A string the regex must not match |

5. Categories a JSON pack may use:

   - `instruction_override`
   - `role_impersonation`
   - `data_exfiltration`
   - `tool_abuse`
   - `jailbreak_persona`
   - `delimiter_injection`

   Hidden Unicode and hidden HTML are Python detectors. They are not JSON categories.

6. Keep the expression bounded. The loader rejects `.*` and `.+` (a dot that is not escaped, followed by `*` or `+`). Those patterns scan the whole document and cause false positives. Prefer `\b` and a short list of words.
7. The loader compiles every file at import time. It checks that `example` matches and `benign_example` does not. A broken rule fails before any scan.
8. Add the code to `KNOWN_LANGUAGES` in `myxguard/detectors/patterns.py`. German (`de`) also loads Swiss German (`gsw`) inside `expand_languages`. Copy that idea only when the extra pack should always travel with the parent. Say so in a comment.
9. Add rows to `datasets/samples.jsonl`. Each line is a JSON object:

   ```json
   {"text": "...", "label": "malicious", "language": "es", "category": "instruction_override", "source": "myxguard-original"}
   ```

   `label` is `malicious` or `benign`. Include boring benign sentences and a few tricky ones (a security article that quotes the attack, a word that shares letters with a rule). Write the examples yourself unless the source license allows reuse. If you reuse text, record it in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
10. Run the checks:

    ```bash
    python -m pytest -q
    python scripts/benchmark.py datasets/samples.jsonl
    ```

`common.json` (`_meta.language` is `multi`) is always loaded. Put a rule there only when it is the same in every language (a special token such as `<|im_start|>`, or the name DAN).

## Add a pattern to a language that already exists

Append one object to that file's `patterns` list. Follow the same fields. Tighten the regex until `benign_example` is a sentence a person might really write. Then add one malicious and one benign JSONL row and run pytest.

A phrase that is only dangerous inside a quote, or only in a lecture, should still match. The discussion downgrade in `myxguard/context.py` lowers the severity. Do not delete the finding.

## What not to copy

Only MIT, Apache-2.0, and CC-BY-4.0 material may be adapted, and only after you have opened the license file yourself. Record the source URL, license, copyright holder, and what you changed.

Do not copy:

- anything from a repository with no license
- the Lakera PINT corpus
- the `data/pint-benchmark` corpus from agent-threat-rules
- names or branding from that project

Do not mark a file as adapted if you only read it and wrote a new check. Say "consulted, not copied" in the third-party notice instead.

Apache-2.0 derivatives need a notice in the file that you changed it, and the license text in `LICENSES/Apache-2.0.txt` stays in the tree.

## Tests

Put detector tests in `tests/`. One behaviour per test, with a name that says what failed. Cover the hit and a near miss. CLI tests should go through `python -m myxguard` so the exit code is real. MCP tests can call `handle_message` directly and should keep one subprocess roundtrip that speaks `Content-Length`.

## Code style

- Prefer a straight function over a class when there is no state to keep.
- Name the rule after the trick (`ignore_previous`), not after a number.
- Comments should help a beginner see the trap (why U+202C is not an override, why a cookie banner is low). Do not restate the next line.
