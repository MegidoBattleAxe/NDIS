---
name: webapp-testing
description: Use when a local web app or UI needs end-to-end verification in a real browser. Drives Playwright through user journeys, captures console errors and screenshots, and reports failures with reproduction steps.
license: MIT
compatibility: Requires Playwright and a locally running app
user-invocable: true
allowed-tools:
  - bash
  - read_file
  - write_file
---

# Webapp testing

Verify a local web app in a real browser before calling a task done.

## Workflow

1. Confirm the app is running locally (start it with `bash` if needed) and note the URL.
2. Write a Playwright script covering the critical user journeys: load, main action, error path, and one edge case (empty input, slow network).
3. Run it headless; capture screenshots on failure to `artifacts/`.
4. Collect console errors and failed network requests; treat uncaught console errors as failures.
5. Report: pass/fail per journey, screenshots, console errors, and exact reproduction steps for each failure. Do not fix the app unless asked.

## Rules

- Test against the local dev server only, never a production URL.
- Reset state between journeys so tests are independent.
- Timeouts: fail fast (10s per navigation) so a hung app does not stall the run.
