---
name: document-processing
description: "Use when creating, parsing, or editing DOCX, PDF, XLSX, PPTX, CSV, or image files. In this repo: parsing incident form attachments (incident_agent/parsers.py) and producing the incident register spreadsheet (incident_agent/spreadsheet.py)."
license: MIT
compatibility: Requires Python with the libraries in requirements.txt
user-invocable: true
allowed-tools:
  - bash
  - read_file
  - write_file
  - grep
---

# Document processing

Work with office and PDF documents deterministically via Python scripts, not by hand.

## Workflow

1. Identify the format from content (magic bytes), not the file extension.
2. Parse with the appropriate library: PDF (pdfminer/pypdf), DOCX and XLSX (python-docx/openpyxl), images (OCR where needed), CSV/JSON/TXT directly.
3. For incident forms in this repo: extract fields, normalise names (`date_of_incident` -> `incident_date`, `client_name` -> `participant`), and never execute or macro-enable anything.
4. For output documents: write with openpyxl/python-docx, keep formatting explicit (fills, filters, frozen panes as in `spreadsheet.py`), and verify by re-reading the file.
5. Report extracted/written data as a table in chat.

## Rules

- Malformed input must produce a clean rejection, not a crash of the whole run.
- Never enable macros, external links, or embedded objects.
- Large files: stream or chunk instead of loading everything into memory.
