---
name: plan-before-build
description: Use when starting any multi-step task (more than 5 tool calls) such as a new parser, a refactor, or a feature. Creates task_plan.md and progress.md on disk so the plan survives context compaction and can be resumed.
license: MIT
compatibility: Requires file writes
user-invocable: true
allowed-tools:
  - read_file
  - write_file
  - grep
  - bash
---

# Plan before build

Turn a vague request into an executable plan before writing code.

## Workflow

1. Write `task_plan.md`: the goal, the ordered steps (each one verifiable), the files to touch, and the definition of done (tests to run, e.g. `python -m pytest tests/ -q` plus demo smoke run for this repo).
2. Write `progress.md` with each step marked pending; update it after every step (done / blocked + why).
3. Execute steps in order. If a step reveals the plan is wrong, update `task_plan.md` first, then continue.
4. When all steps are done, mark the plan complete in `progress.md` and summarise in chat: what changed, where, and how it was verified.

## Rules

- One plan per task; do not stack unrelated work into it.
- Keep plans short: steps should be minutes of work, not hours.
- Disk files beat memory: never rely on conversation history for plan state.
