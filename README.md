# NDIS Incident Intake Agent

Scans an Outlook mailbox for incident-form emails from `info@1myp.com`, downloads every
attachment into one folder (`downloads/`), parses each form, classifies severity and NDIS
reportability, and maintains a single spreadsheet (`output/incident_register.xlsx`) sorted by
severity with **NDIS-reportable incidents highlighted red**.

## How it works

```
Outlook (Microsoft Graph)                local agent                        outputs
----------------------        ------------------------------------        ---------------------------
mail from info@1myp.com  -->  verify sender + validate attachment  -->  downloads/   (all raw forms, one place)
   with attachments             (allowlist, magic bytes, size cap)        output/incident_register.xlsx
                              -->  parse form (PDF/DOCX/XLSX/CSV/JSON/TXT/PNG)
                              -->  classify severity + NDIS reportability
                              -->  write register sorted by severity, reportable rows in red
```

- `incident_agent/graph_client.py` - Microsoft Graph calls. Two auth modes:
  - `device_code` (default): signs in as **your** mailbox interactively on first run, caches a
    refresh token in `.token_cache.json`. Best for "scan my Outlook".
  - `client_credentials`: app-only access to a dedicated monitored mailbox (e.g. a shared
    `incidents@...` mailbox). Best for an unattended agent.
- `incident_agent/safety.py` - attachment validation before anything is parsed: extension
  allowlist (pdf/docx/xlsx/csv/txt/json/png/jpg), magic-byte sniffing (rejects e.g. an `.exe`
  renamed to `.pdf`), 25 MB size cap. Files are stored under a SHA-256-prefixed name and are
  never executed or opened by the OS.
- `incident_agent/parsers.py` - extracts fields from each form format and normalises common
  field names (`date_of_incident` -> `incident_date`, `client_name` -> `participant`, ...).
- `incident_agent/classify.py` - severity (Critical/High/Medium/Low) and NDIS reportability
  rules (see below). Edit the keyword tables here to tune classification.
- `incident_agent/spreadsheet.py` - writes `incident_register.xlsx` with two sheets:
  - **Incident Register**: sorted Critical -> Low; reportable rows filled red (`FFC7CE`) with a
    computed report window (24h / 120h) and report deadline; severity cell colour-coded;
    autofilter + frozen header.
  - **Summary**: totals, per-severity counts, reportable count and source files.
- `incident_agent/agent.py` - orchestration, dedup via `state.json` (each message processed
  once), append-only `output/run_log.jsonl` audit trail.

## Quick start (offline demo)

```bash
pip install -r requirements.txt
python scripts/make_samples.py samples     # generate 6 sample forms
python -m incident_agent --demo --samples samples
# open output/incident_register.xlsx
```

Re-running is safe: already-processed messages are skipped, so the register is never duplicated.
If `output/` is deleted while `state.json` remains, the run prints a `WARNING` and logs a
`register_divergence` event (the register is rebuilt without previously processed rows) -
restore `output/` or delete `state.json` to reprocess.

The spreadsheet produced by the demo run is checked in at [examples/incident_register.xlsx](examples/incident_register.xlsx) so you can preview it in the browser. Live registers stay local in `output/` (gitignored - they contain incident data).

## Live setup against your Outlook

1. **Azure app registration** (Azure Portal > Entra ID > App registrations > New registration):
   - Accounts: "Accounts in this organisational directory only".
   - Redirect URI: `Public client/native` -> `https://login.microsoftonline.com/common/oauth2/nativeclient`,
     and enable **Allow public client flows** (needed for device code).
2. **API permissions** > Microsoft Graph:
   - `device_code` mode: add delegated `Mail.Read`, `User.Read`, `offline_access`, then **Grant admin consent**.
   - `client_credentials` mode: add application `Mail.Read` (and `Mail.ReadBasic` if required), then **Grant admin consent**.
   - In `client_credentials` mode also create a **client secret** under Certificates & secrets.
3. Copy `config.example.env` to `config.env` and fill in:
   - `NDIS_TENANT_ID`, `NDIS_CLIENT_ID`, `NDIS_CLIENT_SECRET` (client-credentials mode only),
   - `NDIS_MAILBOX` (the mailbox to scan),
   - `NDIS_AUTH_MODE=device_code` (personal mailbox) or `client_credentials` (service mailbox),
   - `NDIS_SENDER=info@1myp.com`, `NDIS_ORG_NAME=Origin Support Services`.
4. Run:

```bash
python -m incident_agent --env config.env                    # one scan
python -m incident_agent --env config.env --interval 300     # scan every 5 minutes
python -m incident_agent --env config.env --export-csv       # also write output/incident_register.csv
# or via cron (every 5 minutes):
# */5 * * * * cd /path/to/ndis-incident-agent && /path/to/venv/bin/python -m incident_agent --env config.env >> output/cron.log 2>&1
```

First run in `device_code` mode prints a URL + code - sign in once with the mailbox account.

## NDIS reportability rules encoded

Defaults in `incident_agent/classify.py` follow the NDIS Quality and Safeguards Commission's
incident reporting requirements for registered providers:

- **Reportable within 24 hours**: death of a participant; serious injury; abuse; neglect;
  sexual misconduct; unlawful sexual/physical contact or assault.
- **Reportable within 5 days**: use of a restrictive practice that is not authorised / not in
  accordance with the participant's behaviour support plan.

These rows are flagged `NDIS Reportable = YES` and highlighted red, with the report window and a
computed deadline column. **Verify the keyword tables against the current NDIS Commission
guidance and your organisation's incident management policy** - this tool flags incidents for
review, it does not submit anything to the NDIS portal. Reporting to the Commission is a manual
step you remain responsible for.

## Security notes

- Email attachments are a common malware vector. Before enabling live mode, confirm that
  `info@1myp.com` is genuinely the forms address your organisation uses - the agent enforces an
  exact (case-insensitive) sender match on top of the Graph query filter, but you should still
  confirm the domain.
- Only allowlisted file types are parsed, content is magic-byte checked, capped at 25 MB, and
  stored unopened in `downloads/`. Zip-based formats (docx/xlsx) are additionally rejected if
  they declare more than 10x the size cap uncompressed (zip-bomb guard), and corrupt archives
  are rejected. Inline/signature images are skipped. Rejected files are
  logged in `output/run_log.jsonl`.
- `.token_cache.json` and any `config.env` contain credentials - keep them out of version control
  (the token file is written with `0600` permissions).

## Layout

```
ndis-incident-agent/
  incident_agent/          the agent package
  scripts/make_samples.py  generates sample forms for the demo
  samples/                 generated demo forms
  tests/                   pytest suite (25 tests)
  config.example.env       template for live credentials
  downloads/               all downloaded forms (created on first run)
  output/                  incident_register.xlsx + run_log.jsonl (created on first run)
  state.json               processed-message state (created on first run)
```

## Tests

```bash
python -m pytest tests/ -q
```

CI (`.github/workflows/ci.yml`) runs the test suite plus a demo smoke run on every PR and push to `main` / `vibe/**`.
