---
name: data-analysis
description: Use when asked to analyze data files (CSV, JSON, JSONL, XLSX) such as output/run_log.jsonl or the incident register. Runs SQL/Python locally, produces tables, charts, and a written summary with the commands used.
license: MIT
compatibility: Requires Python with pandas/duckdb or sqlite3
user-invocable: true
allowed-tools:
  - bash
  - read_file
  - write_file
  - grep
---

# Data analysis

Answer questions about data with real queries, not guesses.

## Workflow

1. Inspect the schema first: columns/keys, row count, date ranges, nulls. For JSONL (e.g. `output/run_log.jsonl`) print the keys of the first record.
2. Choose the tool: `sqlite3`/`duckdb` SQL for relational queries, pandas for reshaping, plain Python for JSONL.
3. Run the analysis in small steps, printing intermediate results. Save any chart to `analysis/` as PNG.
4. Write the summary to `analysis/summary.md`: question, query used, result table, caveats (missing data, timezone assumptions), and the exact commands so the analysis is reproducible.
5. Report the headline numbers in chat.

## Rules

- Never load an entire large file into memory if it can be streamed (JSONL) or queried in place (duckdb over CSV/XLSX).
- State assumptions explicitly (e.g. timezone of `received` timestamps when computing report deadlines).
- Do not modify the source data files; write outputs only under `analysis/`.
