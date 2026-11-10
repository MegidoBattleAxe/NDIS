---
name: repo-onboarding
description: "Use when an agent starts working in a repo for the first time, or when repo conventions are not yet codified. Produces or updates AGENTS.md capturing layout, build/test commands, and team conventions so the agent needs no verbal context."
license: MIT
compatibility: Requires read access to the repo
user-invocable: true
allowed-tools:
  - read_file
  - write_file
  - grep
  - glob
  - bash
---

# Repo onboarding

Codify how this repo works so any agent (or new hire) is effective immediately.

## Workflow

1. Survey the repo: README, package layout, tests, CI workflow, config templates, git history for conventions.
2. Write or update `AGENTS.md` at the repo root with: what the project does, layout map, how to run tests (`python -m pytest tests/ -q`), how to run the demo (`python scripts/make_samples.py samples && python -m incident_agent --demo --samples samples`), what must never be committed (`config.env`, `.token_cache.json`, `output/`, `downloads/`), and where to put new skills (`.vibe/skills/`).
3. Keep it factual and short (under 100 lines); link to README for detail.
4. Verify every command in the file actually runs.

## Rules

- Derive content from the repo itself, not from generic templates.
- Do not duplicate the README; point to it.
- Update the file whenever conventions change.
