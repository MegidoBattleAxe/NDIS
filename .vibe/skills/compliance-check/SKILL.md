---
name: compliance-check
description: "Use before committing or shipping anything that touches incident data. Verifies PII handling and redaction, retention, gitignore coverage of output/ and downloads/, NDIS reportability rules against current Commission guidance, and that no real participant data enters the repo."
license: MIT
compatibility: Requires read access to the repo and git
user-invocable: true
allowed-tools:
  - read_file
  - grep
  - glob
  - bash
---

# Compliance check

Verify NDIS/GDPR-style handling before anything ships. This agent processes incident data about real participants.

## Workflow

1. **Data in git**: `git status` and `git ls-files` must show no `output/`, `downloads/`, `state.json`, `config.env`, `.token_cache.json`, `samples/` with real data. `examples/incident_register.xlsx` must contain only synthetic demo rows.
2. **PII in code and docs**: grep for participant names, emails, or phone numbers in committed files; postmortems and tests must use synthetic identifiers only.
3. **Secrets**: no tokens/secrets in code, tests, examples, or commit history (`git log -p` spot check on touched files); token cache written `0600`.
4. **Reportability rules**: confirm `incident_agent/classify.py` keyword tables still match current NDIS Commission guidance (24h / 5-day windows); use `deep-research` to verify against the primary source and record the citation.
5. **Access control**: Graph permissions limited to `Mail.Read` / `User.Read` / `offline_access`; sender allowlist is an exact match.
6. Report a table: `Check | Result | Evidence`, ending with a verdict: compliant / blocked with reasons.

## Rules

- When in doubt, treat data as regulated: NDIS incident data is sensitive personal information.
- A check without evidence (file:line, command output, citation) does not count as passed.
