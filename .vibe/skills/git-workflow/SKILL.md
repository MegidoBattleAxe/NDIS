---
name: git-workflow
description: "Use when committing, branching, or opening a PR in this repo. Enforces the repo's conventions: short imperative commit subjects, vibe/<slug> branch names, focused commits, and PR descriptions with summary and verification sections."
license: MIT
compatibility: Requires git and gh
user-invocable: true
allowed-tools:
  - bash
  - read_file
---

# Git workflow

Keep git history and PRs consistent with this repo's conventions.

## Workflow

1. Branch: `vibe/<short-slug>` for work (CI runs on `vibe/**` pushes); never commit directly to `main`.
2. Commit in focused units. Subject line: short imperative, no trailing period (repo style: "Sort register by severity desc, then incident date desc (newest first)"). Body optional, wrapped at 72 chars, explaining why.
3. Never commit `config.env`, `.token_cache.json`, `state.json`, `output/`, `downloads/`, `samples/` - check `git status` before `git add -A`.
4. Push with `git push -u origin <branch>` and open/update the PR with `gh pr create` or push to an existing PR's head branch.
5. PR description: Summary (bullets), Verification (commands run and results), and a `Closes #<n>` line only if it resolves a tracked issue.

## Rules

- One logical change per commit; split with `git add -p` if needed.
- Run the test suite before pushing: `python -m pytest tests/ -q`.
- Do not force-push shared branches; if history was rewritten, use `--force-with-lease` only on your own PR branch.
