---
name: systematic-debugging
description: Use when something is broken and the cause is not obvious. Replaces trial-and-error edits with a four-phase root-cause process and requires evidence before proposing a fix.
license: MIT
compatibility: Requires bash and read access to the repo
user-invocable: true
allowed-tools:
  - bash
  - read_file
  - grep
  - write_file
---

# Systematic debugging

Find the root cause before changing code.

## Four phases

1. **Reproduce**: get a minimal, deterministic reproduction (a command, a sample file, a test). Record the exact error output.
2. **Localise**: bisect with evidence - add temporary logging, run the smallest input that still fails, read the stack trace to the frame where the invariant breaks. For this repo, check `output/run_log.jsonl` for the failing message.
3. **Hypothesise**: write down one cause you can prove or disprove. Test it with a targeted experiment (a one-off Python snippet), not by editing the code.
4. **Fix and verify**: apply the smallest fix, re-run the reproduction, then the full suite `python -m pytest tests/ -q`. If the fix fails verification, go back to phase 2 - do not stack a second guess on top.

## Rules

- One hypothesis at a time; never change two things in one step.
- Every claim about the cause must cite evidence (log line, test output, code line).
- If stuck after two failed hypotheses, write down what you know and ask the user instead of guessing further.
