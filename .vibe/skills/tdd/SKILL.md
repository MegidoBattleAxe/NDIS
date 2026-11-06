---
name: tdd
description: Use when adding a parser, classification rule, or any behaviour change to incident_agent. Enforces a test-first loop so behaviour is proven before the implementation is expanded.
license: MIT
compatibility: Requires pytest
user-invocable: true
allowed-tools:
  - read_file
  - write_file
  - bash
  - grep
---

# Test-driven development

Apply a strict red-green-refactor loop. Use when the request adds or changes behaviour in `incident_agent/`.

## Loop

1. **Red**: write a failing test in `tests/` that names the exact expected behaviour (e.g. a sample form that must classify as Critical/reportable, a malicious attachment that must be rejected). Run `python -m pytest tests/ -q` and confirm it fails for the right reason.
2. **Green**: implement the smallest change that makes the test pass. No extra features.
3. **Refactor**: clean up only after green; re-run the full suite.
4. Repeat per behaviour. Do not batch multiple behaviours into one test.

## Rules

- Tests use the existing fixtures and sample-generation style in `tests/` and `scripts/make_samples.py`; never put real incident data in tests.
- New classifier keyword tables in `incident_agent/classify.py` need at least one positive and one negative test each.
- New parsers in `incident_agent/parsers.py` need a malformed-input test (truncated, wrong type, empty) asserting a clean rejection, not an exception that kills the run.
- Finish by running the full suite plus the demo smoke run: `python scripts/make_samples.py samples && python -m incident_agent --demo --samples samples`.
