---
name: skill-creator
description: "Use when creating a new SKILL.md skill in .vibe/skills/ or ~/.vibe/skills/. Enforces the Agent Skills spec: valid YAML frontmatter, a trigger-rich description under 1024 characters, allowed-tools list, and a validation pass before the skill is considered done."
license: MIT
compatibility: Requires file writes and Python for validation
user-invocable: true
allowed-tools:
  - read_file
  - write_file
  - bash
---

# Skill creator

Author a new skill that Vibe will actually discover and invoke correctly.

## Workflow

1. Create `.vibe/skills/<kebab-name>/SKILL.md`. The directory name must equal the frontmatter `name`.
2. Frontmatter: `name`, `description`, `license`, `compatibility`, `user-invocable: true`, `allowed-tools`. Quote the description if it contains a colon.
3. The `description` is the trigger: start with "Use when ..." and name the concrete situations that should load the skill. Keep it under 1,024 characters.
4. Body: numbered workflow, then Rules. Be specific - steps the agent can follow without asking.
5. Validate: parse the frontmatter as YAML, check `name` == directory, description length, non-empty body. Fix any failure before finishing.

## Rules

- One skill = one workflow. Split broad skills instead of writing a manual.
- If the skill can touch files, say which paths it may write.
- Never put secrets or real data in a skill; skills are committed to the repo.
