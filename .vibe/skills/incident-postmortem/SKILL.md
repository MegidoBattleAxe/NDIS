---
name: incident-postmortem
description: "Use after a real incident involving this agent or the NDIS reporting process, for example a misclassified severity, a missed 24h/5-day report window, or an outage. Writes a blameless postmortem with timeline, root cause, reportability impact, and action items under postmortems/."
license: MIT
compatibility: Requires file writes and read access to output/run_log.jsonl
user-invocable: true
allowed-tools:
  - read_file
  - write_file
  - grep
  - bash
---

# Incident postmortem

Write a blameless postmortem for an incident. Focus on the system, never on individuals.

## Workflow

1. Gather evidence first: `output/run_log.jsonl`, `state.json`, the register rows involved, and the original form. Quote exact timestamps.
2. Write `postmortems/YYYY-MM-DD-<slug>.md` with sections:
   - Summary (one paragraph: what happened, impact, was anything reportable to the NDIS Commission and within what window).
   - Timeline (table: time, event, source). Include the computed report deadline and whether it was met.
   - Root cause (use the four phases from `systematic-debugging`; cite evidence).
   - What went well / what went badly.
   - Action items (table: item, owner, due date, how we will verify it is done - e.g. a new test in `tests/` or a keyword added in `classify.py`).
3. If classification was wrong, link the specific keyword-table change in `incident_agent/classify.py` that fixes it and note that it needs a test.
4. Review the draft with a human before sharing; remove any participant-identifying details (use participant IDs, not names).

## Rules

- Blameless language only; describe process failures, not personal mistakes.
- Every action item must be verifiable (test, doc, or config change).
- Never paste real participant data into the postmortem file that gets committed.
