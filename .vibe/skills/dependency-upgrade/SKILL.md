---
name: dependency-upgrade
description: "Use when bumping packages in requirements.txt or adding a dependency. Upgrades in small batches, reads changelogs for breaking changes, and runs the full test suite plus the demo smoke run after each batch."
license: MIT
compatibility: Requires pip and pytest
user-invocable: true
allowed-tools:
  - bash
  - read_file
  - write_file
  - grep
---

# Dependency upgrade

Upgrade dependencies safely, in small verifiable batches.

## Workflow

1. List outdated packages: `pip list --outdated` (in the project venv).
2. Read `requirements.txt` and group upgrades: security fixes first, then minor bumps, then major versions one at a time.
3. For each batch: check the package changelog/release notes for breaking changes, bump the pin, `pip install -r requirements.txt`, then run `python -m pytest tests/ -q` and the demo smoke run (`python scripts/make_samples.py samples && python -m incident_agent --demo --samples samples`).
4. If a batch fails, revert that batch only and record why in the PR description.
5. Never upgrade everything at once; never add a dependency that is not used in code.

## Rules

- One major version per commit so a failure is attributable.
- Keep pins exact (`==`) as the repo currently does.
- After all batches: full suite + smoke run again, then summarize versions old -> new.
