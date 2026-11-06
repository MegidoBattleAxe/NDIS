# Spec: register/state divergence warning

Fixes the High finding in `audits/security-audit-2026-11-06.md`.

## Goal

Make register/state divergence loud instead of silent: if the register file is missing
(or its row count disagrees with state) while `state.json` says messages were already
processed, the run must warn on stderr and log an event — never rebuild an empty
register quietly.

## Requirements

1. `state.json` gains a `register_row_count` field, written after every successful
   register write (`run_once`), equal to the number of rows in the register.
2. On every `run_once`, before writing the register (using the state as loaded at run
   start, i.e. counts from *previous* runs, not messages processed in this run):
   - If the register file does **not** exist and the previously processed
     `processed_message_ids` is non-empty:
     log `{"event": "register_divergence", ...}` to `run_log.jsonl` and print a
     `WARNING:` line to stderr explaining that the register is being rebuilt without
     previously processed rows and how to recover (restore `output/` or delete
     `state.json` to reprocess).
   - If the register exists, `register_row_count` is present in state, and the
     actual register row count differs: log `register_row_count_mismatch` and print a
     `WARNING:` to stderr.
3. No warning when register and state agree (normal idempotent re-run stays quiet).
4. Existing behaviour otherwise unchanged: same register contents, same dedup, same
   return stats. No new dependencies, no CLI changes.

## Non-goals

- Automatic rebuild of lost rows from `downloads/` (rows need message metadata that is
  not stored); the fix is detection + loud warning, per the audit remediation.
- Changing the xlsx format or state schema beyond adding `register_row_count`.

## Acceptance criteria (tests in `tests/test_register_divergence.py`)

- AC1: demo run, delete xlsx, run again -> stderr has `WARNING`, run_log has
  `register_divergence`, register rebuilt with 0 rows. -> `test_warns_when_register_missing`
- AC2: normal second demo run -> no `WARNING` on stderr, no divergence events.
  -> `test_quiet_when_consistent`
- AC3: state.json contains `register_row_count` == rows after a run.
  -> `test_state_records_register_row_count`
- AC4: tampered `register_row_count` in state -> `register_row_count_mismatch` logged
  + stderr warning. -> `test_warns_on_row_count_mismatch`

## Open questions

None.
