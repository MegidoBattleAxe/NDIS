---
name: release-check
description: "Use before merging or shipping a change in this repo. Runs the pre-ship checklist: full test suite, demo smoke run, secrets/artifact hygiene, docs updated, and a summary of what changed."
license: MIT
compatibility: Requires pytest and the repo checked out
user-invocable: true
allowed-tools:
  - bash
  - read_file
  - grep
  - glob
---

# Release check

Run the pre-ship checklist and report pass/fail per item. Do not merge if any item fails.

## Checklist

1. **Tests**: `python -m pytest tests/ -q` - all pass.
2. **Smoke run** (mirrors CI): `python scripts/make_samples.py samples && python -m incident_agent --demo --samples samples && test -f output/incident_register.xlsx`.
3. **Hygiene**: `git status` shows no `config.env`, `.token_cache.json`, `state.json`, `output/`, `downloads/`, or `samples/` staged; `git diff` contains no secrets, tokens, or real participant data.
4. **Docs**: README updated if behaviour, config keys, or commands changed; classification keyword-table changes in `classify.py` are reflected in the README rules section.
5. **Classification sanity**: spot-check one sample per severity and one reportable/unreportable pair against `classify.py` rules.
6. **Summary**: report the diffstat, test count, smoke-run result, and a one-paragraph change summary suitable for the PR description.

## Output

Table: `Check | Result | Evidence`. End with an overall verdict: ready to ship / blocked, listing any failures.
