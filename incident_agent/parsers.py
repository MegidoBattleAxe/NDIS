import csv
import io
import json
import re
import zipfile
from html import unescape
from pathlib import Path

FIELD_ALIASES = {
    "incident_date": ["date", "incident_date", "date_of_incident", "occurred_on", "date_occurred", "event_date"],
    "participant": ["participant", "participant_name", "client", "client_name", "person", "resident", "service_user"],
    "incident_type": ["type", "incident_type", "category", "incident_category", "event_type", "nature_of_incident"],
    "description": ["description", "details", "narrative", "summary", "what_happened", "incident_description", "comments"],
    "severity": ["severity", "priority", "seriousness", "level"],
    "location": ["location", "site", "place", "venue", "address"],
    "reported_by": ["reported_by", "reporter", "staff", "staff_name", "submitted_by", "author"],
    "actions_taken": ["actions", "actions_taken", "response", "immediate_actions", "follow_up", "outcome"],
    "injuries": ["injuries", "injury", "harm", "harm_description"],
    "restrictive_practice": ["restrictive_practice", "restrictive practice", "restraint", "restrictive_practice_used"],
}

KV_LINE = re.compile(r"^\s*([A-Za-z][A-Za-z0-9 _/()-]{1,60}?)\s*[:：]\s*(.+?)\s*$")


def _alias_key(key):
    norm = re.sub(r"[^a-z0-9]+", "_", key.strip().lower()).strip("_")
    for canonical, aliases in FIELD_ALIASES.items():
        if norm == canonical or norm in aliases:
            return canonical
    return norm


def normalize_record(raw):
    out = {}
    for key, value in raw.items():
        if value is None:
            continue
        out[_alias_key(str(key))] = str(value).strip()
    return out


def parse_kv_text(text):
    record = {}
    loose = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        m = KV_LINE.match(line)
        if m:
            record[_alias_key(m.group(1))] = m.group(2)
        else:
            loose.append(line)
    if not record and loose:
        record["description"] = "\n".join(loose)
    elif loose and "description" not in record:
        record["description"] = "\n".join(loose)
    return record


def _parse_json(data):
    payload = json.loads(data.decode("utf-8-sig"))
    if isinstance(payload, dict):
        payload = payload.get("incidents") or payload.get("records") or [payload]
    if not isinstance(payload, list):
        raise ValueError("json attachment must be an object or a list of objects")
    return [normalize_record(item) for item in payload if isinstance(item, dict)]


def _parse_csv(data):
    text = data.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    return [normalize_record(row) for row in reader]


def _parse_txt(data):
    return [normalize_record(parse_kv_text(data.decode("utf-8-sig")))]


def _parse_docx(data):
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        xml = zf.read("word/document.xml").decode("utf-8")
    xml = xml.replace("</w:p>", "\n")
    text = unescape(re.sub(r"<[^>]+>", "", xml))
    return [normalize_record(parse_kv_text(text))]


def _parse_xlsx(data):
    from openpyxl import load_workbook

    wb = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    ws = wb.worksheets[0]
    rows = [list(r) for r in ws.iter_rows(values_only=True)]
    wb.close()
    rows = [r for r in rows if any(c is not None and str(c).strip() for c in r)]
    if not rows:
        return []
    headers = [str(c).strip() if c is not None else "" for c in rows[0]]
    records = []
    for row in rows[1:]:
        raw = {h: v for h, v in zip(headers, row) if h}
        records.append(normalize_record(raw))
    return records


def _parse_pdf(data):
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    text = "\n".join((page.extract_text() or "") for page in reader.pages)
    return [normalize_record(parse_kv_text(text))]


def parse_attachment(name, data):
    ext = Path(name).suffix.lower()
    if ext == ".json":
        return _parse_json(data)
    if ext == ".csv":
        return _parse_csv(data)
    if ext == ".txt":
        return _parse_txt(data)
    if ext == ".docx":
        return _parse_docx(data)
    if ext == ".xlsx":
        return _parse_xlsx(data)
    if ext == ".pdf":
        return _parse_pdf(data)
    if ext in (".png", ".jpg", ".jpeg"):
        return [{"incident_type": "photo evidence", "description": f"photo attachment: {name}"}]
    raise ValueError(f"no parser for {ext}")
