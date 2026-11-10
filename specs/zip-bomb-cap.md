# Spec: zip-bomb cap for archive-based attachments

Fixes the Medium finding in `audits/security-audit-2026-11-06.md`.

## Goal

Reject ZIP-based attachments (docx/xlsx) whose declared uncompressed size is
implausibly large relative to the download cap, so a small "form" cannot expand into a
memory/CPU bomb during parsing. Enforcement point: `validate_attachment` in
`incident_agent/safety.py`, before any parser touches the data.

## Requirements

1. New helper `archive_declared_bytes(data)` in `safety.py`: opens the bytes as a
   `zipfile.ZipFile` and returns the sum of `ZipInfo.file_size` over all members;
   returns `None` if the data is not a readable zip (corrupt archive).
2. In `validate_attachment`, when the sniffed kind is `.zip` (i.e. docx/xlsx):
   - `None` -> reject with reason containing "corrupt".
   - declared total > `max_bytes * ARCHIVE_EXPANSION_LIMIT` -> reject with reason
     containing "uncompressed" and the limit.
3. `ARCHIVE_EXPANSION_LIMIT = 10` (module constant): a 25 MB download may declare at
   most 250 MB uncompressed. Normal incident forms are far below this.
4. Non-archive types (pdf/png/jpg/text) are unaffected.
5. Existing accepted files (the demo samples) must still validate.

## Non-goals

- Streaming/decompressed-while-reading limits inside openpyxl/python-docx (declared-size
  check is the mitigation; noted as residual risk in the audit report).
- Changes to the 25 MB download cap itself.

## Acceptance criteria (tests in `tests/test_safety.py`)

- AC1: zip declaring > limit uncompressed bytes is rejected. -> `test_rejects_zip_bomb`
- AC2: small real docx zip still accepted. -> `test_accepts_valid_docx_zip` (fixture
  upgraded to a real zip)
- AC3: corrupt zip (PK magic, garbage body) rejected with "corrupt".
  -> `test_rejects_corrupt_zip`
- AC4: demo samples still pass validation (covered by `test_agent_demo.py`).

## Open questions

None.
