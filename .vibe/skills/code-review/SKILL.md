---
name: code-review
description: Use when reviewing code changes or pull requests in this repo (incident_agent package) or any other project. Produces findings ranked by severity with a security-first checklist covering attachment handling, secrets, and input validation.
license: MIT
compatibility: Requires git
user-invocable: true
allowed-tools:
  - read_file
  - grep
  - glob
  - bash
---

# Code review

Review the diff or the named files and report findings. Do not fix anything unless asked.

## Workflow

1. Get the changes: `git diff main...HEAD` for a branch, `git diff` for unstaged, or read the files named in the request.
2. Read the full changed files, not just the hunks, so findings account for surrounding code.
3. Check each area below, in order. Stop early only if the change is trivial.

## Checklist (security first)

1. **Security**
   - Untrusted input: email attachments, form fields, filenames. For this repo: confirm `incident_agent/safety.py` allowlist, magic-byte sniffing, size cap, and `_SAFE_NAME` sanitisation cannot be bypassed (e.g. double extensions, `..` in names, zip-in-docx).
   - Secrets: no credentials, tokens, or keys in code, tests, or examples; `config.env` / `.token_cache.json` must stay gitignored; token file written with `0600`.
   - Sender allowlist: exact case-insensitive match on the configured sender, not just a Graph query filter.
   - Injection: no shell=True with interpolated input, no eval/exec on parsed content, no SQL string building.
2. **Correctness**: off-by-one errors, timezone/naive datetime mix-ups (report deadlines), dedup logic, error paths.
3. **Error handling**: no bare `except:`, errors logged to `output/run_log.jsonl` where relevant.
4. **Types and style**: type hints on new functions, match existing module style.
5. **Tests**: every behaviour change needs a test in `tests/`; run `python -m pytest tests/ -q`.

## Output format

Report as a table: `Severity | File:line | Finding | Suggested fix`. Severities: Critical (security/credential/data-loss), High (correctness bug), Medium (robustness/style), Low (nit). End with a one-line verdict: approve / approve with nits / request changes.
