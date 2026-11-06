---
name: deep-research
description: Use for multi-step research questions that need several sources, cross-checking, and citations, such as verifying NDIS Commission incident-reporting rules, Microsoft Graph API behaviour, or parser library behaviour. Writes findings to disk so long sessions do not lose context.
license: MIT
compatibility: Requires web search and file writes
user-invocable: true
allowed-tools:
  - bash
  - read_file
  - write_file
  - grep
---

# Deep research

Run a structured research pass and deliver a cited brief. Use when the question needs more than one source or a definitive answer.

## Workflow

1. Create `research/task_plan.md` with the sub-questions to answer.
2. For each sub-question: search, open the primary source (official docs, regulator guidance, RFC/library docs) before secondary sources, and record `research/findings.md` entries as: question, answer, source URL, date checked, confidence (high/medium/low).
3. Cross-check: any claim that affects compliance (e.g. NDIS reportability windows of 24h / 5 days) must be confirmed against the current primary source, and note the exact guidance title and date.
4. Update `research/progress.md` as you go so a resumed session knows what is done.
5. Finish with a summary in chat: the answer, the key citations as links, open questions, and anything that contradicted earlier assumptions.

## Rules

- Prefer primary sources (NDIS Commission, Microsoft Learn, official library docs) over blogs.
- Never state a compliance deadline without a citation.
- If sources conflict, report the conflict explicitly instead of picking silently.
