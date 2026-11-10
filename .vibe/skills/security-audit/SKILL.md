---
name: security-audit
description: Use when auditing this agent or a similar service for security risks before enabling live mode. Covers the email-attachment threat model, credential handling, and data exposure, and produces a structured report.
license: MIT
compatibility: Requires read access to the repo and git
user-invocable: true
allowed-tools:
  - read_file
  - grep
  - glob
  - bash
---

# Security audit

Audit the codebase against the stated threat model and produce a structured report. Do not fix issues unless asked.

## Threat model for this repo

The agent reads email from an allowlisted sender, downloads attachments, parses them, and writes a spreadsheet. Attachments are untrusted content.

## Audit areas

1. **Attachment handling** (`incident_agent/safety.py`, `parsers.py`)
   - Extension allowlist vs magic-byte sniffing: can a file claim one type and contain another? Are zip-based formats (docx/xlsx) scanned for embedded executables or external links?
   - Size cap enforced before parsing, not after download to disk.
   - Filename sanitisation (`_SAFE_NAME`) blocks path traversal (`../`, absolute paths, null bytes).
   - Files are stored unopened and never executed; no `subprocess` on attachment content.
2. **Authentication and secrets** (`graph_client.py`, `config.py`)
   - No client secrets in code or tests; `config.env` and `.token_cache.json` gitignored; token cache written `0600`.
   - Sender allowlist is an exact case-insensitive match in code, independent of the Graph filter.
   - Least privilege: only `Mail.Read` / `User.Read` / `offline_access` requested.
3. **Data exposure**
   - `output/` and `downloads/` (incident data) are gitignored; `examples/` contains only synthetic demo data.
   - Audit log `run_log.jsonl` does not log tokens or message bodies.
4. **Dependencies**: `requirements.txt` pins and known-vulnerable versions; parsers handle malformed files without crashing the run (a crash must not block other messages).

## Output format

Table: `Severity | Area | Finding | Evidence (file:line) | Remediation`. Severities: Critical / High / Medium / Low. End with an overall verdict and the single most important fix.
