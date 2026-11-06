---
name: spec-writing
description: "Use when starting a new feature, parser, or behaviour change in this repo. Writes a spec (goal, requirements, non-goals, acceptance criteria) under specs/ before any code, and interrogates the requester one question at a time until the spec is unambiguous."
license: MIT
compatibility: Requires file writes
user-invocable: true
allowed-tools:
  - read_file
  - write_file
  - grep
  - ask_user_question
---

# Spec writing

No code before the spec is approved.

## Workflow

1. Read the relevant code first (`incident_agent/` modules, README) so the spec is grounded in how the agent actually works.
2. Write `specs/<feature>.md` with sections: Goal, Requirements (numbered, testable), Non-goals, Acceptance criteria (each mapped to a test), Open questions.
3. If anything is ambiguous, ask the user one question at a time (via `ask_user_question`) and record the answer in the spec. Do not guess.
4. Present the spec for approval. Only after approval move to implementation (use `plan-before-build`).

## Rules

- Every requirement must be verifiable by a test or a demo run; if it cannot be, reword it.
- For classification changes, state the exact NDIS category and report window affected.
- Keep the spec under one page; link to code instead of pasting it.
