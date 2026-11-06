---
name: code-simplify
description: "Use after a feature lands, or when code is flagged as hard to read. Refactors for clarity (naming, extraction, dead-code removal) without changing behaviour, proven by the unchanged test suite."
license: MIT
compatibility: Requires pytest
user-invocable: true
allowed-tools:
  - read_file
  - write_file
  - grep
  - bash
---

# Code simplify

Make the code clearer without changing what it does.

## Workflow

1. Run the full suite first (`python -m pytest tests/ -q`) and record the baseline: all green.
2. Pick one module (e.g. a function in `incident_agent/`). Simplify in this order: remove dead code, rename for intent, extract long functions (over ~30 lines), flatten nested conditionals, drop unused parameters.
3. After each change, re-run the full suite. Any failure means the change altered behaviour - revert it.
4. Do not change public names used across modules unless you update all call sites and tests.
5. Finish with the demo smoke run to confirm end-to-end behaviour.

## Rules

- Behaviour-preserving only: no new features, no "while I'm here" fixes.
- Clarity over cleverness: prefer explicit over concise if the explicit form reads better.
- If a simplification needs a test change, stop - that is a behaviour change, not a simplification.
