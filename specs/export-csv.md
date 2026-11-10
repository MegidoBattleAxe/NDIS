# Spec: `--export-csv` flag

## Goal

Let operators get the incident register as a plain CSV alongside the Excel workbook,
for tools that cannot read `.xlsx` (e.g. quick greps, other pipelines).

## Requirements

1. New CLI flag `--export-csv` on `python -m incident_agent`. When set, every run
   (demo and live) also writes `output/incident_register.csv` next to
   `output/incident_register.xlsx`.
2. The CSV has the same header row as the "Incident Register" sheet (`HEADERS` in
   `incident_agent/spreadsheet.py`) and the same rows in the same order
   (severity desc, then incident date desc) with the same cell values, so the two
   exports never disagree.
3. Without the flag, behaviour is unchanged: no CSV is written and the run output does
   not mention one.
4. `run_once` stats include `csv_register` (path string) only when the CSV was written.
5. UTF-8 encoding, standard comma-separated quoting (Python `csv` module defaults).

## Non-goals

- No CSV for the Summary sheet.
- No configuration-file switch; CLI flag only.
- No styling/colours in CSV (plain data only).

## Acceptance criteria (each maps to a test in `tests/test_export_csv.py`)

- AC1: demo run with `--export-csv` produces `incident_register.csv` with header +
  one row per incident. -> `test_demo_writes_csv_when_enabled`
- AC2: CSV content equals the xlsx "Incident Register" sheet content row-by-row.
  -> `test_csv_matches_xlsx_register`
- AC3: run without the flag writes no CSV and stats have no `csv_register`.
  -> `test_no_csv_without_flag`
- AC4: CSV rows are sorted like the xlsx (Critical before Low). -> `test_write_register_csv_sorts_like_xlsx`

## Open questions

None - flag semantics are fully determined by the requirements above.
