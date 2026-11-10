---
name: performance-profiling
description: "Use when the agent run is slow and the cause is unknown, for example long demo scans or slow attachment parsing. Profiles first (cProfile, timing around parsing and spreadsheet writes), reports measured hotspots, then optimizes only what the profile justifies."
license: MIT
compatibility: Requires Python with cProfile
user-invocable: true
allowed-tools:
  - bash
  - read_file
  - write_file
  - grep
---

# Performance profiling

Measure before optimizing.

## Workflow

1. Reproduce with a realistic workload: `python scripts/make_samples.py samples` plus a larger synthetic set if needed.
2. Profile the demo run: `python -m cProfile -s cumulative -m incident_agent --demo --samples samples` (write output to `analysis/profile.txt`).
3. Identify the top hotspots by cumulative time. For this repo, watch: attachment download/validation in `safety.py`, per-format parsing in `parsers.py`, and spreadsheet writes in `spreadsheet.py`.
4. Report a table: `Function | File:line | Cum time | Calls | Note`. Mark which are worth optimizing (hot and fixable) vs not (I/O-bound network calls).
5. Only then change code, one hotspot at a time, re-running the profile and the test suite after each change. Keep the before/after numbers in `analysis/`.

## Rules

- No optimization without a profile number justifying it.
- Correctness first: `python -m pytest tests/ -q` must stay green after every change.
- If the bottleneck is network (Graph API), say so and stop - do not "optimize" I/O with cleverness.
