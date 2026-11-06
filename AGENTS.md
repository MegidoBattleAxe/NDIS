# AGENTS.md

Agent instructions for this repository. Read this before making changes.

## What this project is

NDIS incident intake agent: scans an Outlook mailbox (Microsoft Graph) for incident
forms from an allowlisted sender, validates and parses every attachment, classifies
severity and NDIS reportability, and maintains `output/incident_register.xlsx` sorted by
severity with NDIS-reportable rows highlighted red. See [README.md](README.md) for the full
description and live setup.

## Layout

```
incident_agent/            the agent package
  agent.py                 orchestration, dedup via state.json, audit log
  graph_client.py          Microsoft Graph calls (device_code or client_credentials)
  safety.py                attachment validation: extension allowlist, magic bytes, 25 MB cap
  parsers.py               per-format field extraction (PDF/DOCX/XLSX/CSV/JSON/TXT/PNG)
  classify.py              severity + NDIS reportability keyword tables (24h / 5-day windows)
  spreadsheet.py           incident_register.xlsx writer (Register + Summary sheets)
  config.py                env-file loading
scripts/make_samples.py    generates 6 synthetic sample forms
tests/                     pytest suite
.vibe/skills/              agent skills (SKILL.md directories) - add new skills here
examples/                  checked-in demo register (synthetic data only)
config.example.env         template for live credentials
```

## Commands

All commands run from the repo root with `pip install -r requirements.txt` done once.

```bash
python -m pytest tests/ -q                                              # test suite
python scripts/make_samples.py samples                                  # generate sample forms
python -m incident_agent --demo --samples samples                       # offline demo run
python -m incident_agent --env config.env                               # one live scan
python -m incident_agent --env config.env --interval 300                # poll every 5 min
```

CI (`.github/workflows/ci.yml`) runs the test suite plus the demo smoke run on pushes to
`main` and `vibe/**` and on PRs to `main`.

## Conventions

- Commit subjects: short imperative, no trailing period
  (e.g. "Sort register by severity desc, then incident date desc (newest first)").
- Branches: `vibe/<short-slug>` for work; never commit directly to `main`.
- One logical change per commit; run the test suite before pushing.
- PR descriptions: Summary bullets + Verification (commands run, results).
- Dependencies are pinned with `>=` lower bounds in `requirements.txt`; bump in small
  batches and re-run tests after each batch.
- New reusable agent workflows go in `.vibe/skills/<name>/SKILL.md` (Agent Skills spec:
  YAML frontmatter with `name` matching the directory, `description` starting "Use when ...",
  `allowed-tools`).

## Never commit

`config.env`, `.token_cache.json`, `state.json`, `output/`, `downloads/`, `samples/` -
all gitignored; they contain credentials and real incident data. `examples/` must stay
synthetic. Check `git status` before `git add -A`.

## Safety rules (do not weaken)

- Attachments are untrusted: extension allowlist + magic-byte sniffing + 25 MB cap in
  `safety.py`; files are stored unopened under SHA-256-prefixed names, never executed.
- Sender allowlist is an exact case-insensitive match in code, independent of the Graph
  filter (`NDIS_SENDER`).
- Graph permissions are least-privilege: `Mail.Read`, `User.Read`, `offline_access` only.
- Token cache is written with `0600` permissions.
- Classification changes in `classify.py` need tests with one positive and one negative
  case per keyword group, and must stay aligned with current NDIS Commission guidance
  (the tool flags incidents; reporting to the Commission remains a manual step).

## Skills available

20 skills live in `.vibe/skills/` and are invocable as slash commands, e.g.
`/code-review`, `/tdd`, `/security-audit`, `/compliance-check`, `/release-check`,
`/incident-postmortem`, `/spec-writing`. Run `/reload` after adding or editing a skill.
