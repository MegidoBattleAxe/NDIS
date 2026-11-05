import json
from datetime import datetime, timezone
from pathlib import Path

from .classify import classify, parse_received
from .graph_client import GraphClient, since_iso
from .parsers import parse_attachment
from .safety import store_attachment, validate_attachment
from .spreadsheet import write_register

REGISTER_NAME = "incident_register.xlsx"


class IncidentAgent:
    def __init__(self, cfg, client=None):
        self.cfg = cfg
        self.client = client
        self.cfg.ensure_dirs()

    def _load_state(self):
        path = Path(self.cfg.state_file)
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass
        return {"processed_message_ids": [], "last_received": None}

    def _save_state(self, state):
        Path(self.cfg.state_file).write_text(json.dumps(state, indent=2), encoding="utf-8")

    def _log(self, entry):
        entry = dict(entry, at=datetime.now(timezone.utc).isoformat())
        with (self.cfg.output_dir / "run_log.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")

    def _sender_of(self, message):
        return (message.get("from", {}).get("emailAddress", {}) or {}).get("address", "")

    def _ingest_bytes(self, message, name, data):
        ok, reason = validate_attachment(name, data, self.cfg.max_attachment_bytes)
        if not ok:
            self._log({"event": "attachment_rejected", "message_id": message["id"], "file": name, "reason": reason})
            return [], {"file": name, "status": "rejected", "reason": reason}
        stored = store_attachment(self.cfg.downloads_dir, name, data)
        try:
            raw_records = parse_attachment(name, data)
        except Exception as exc:
            self._log({"event": "parse_failed", "message_id": message["id"], "file": name, "error": str(exc)})
            return [], {"file": name, "status": "parse_failed", "reason": str(exc)}
        received = parse_received(message.get("receivedDateTime"))
        rows = []
        for raw in raw_records:
            record = dict(raw)
            record["subject"] = message.get("subject", "")
            record["received"] = message.get("receivedDateTime", "")
            record["source_file"] = stored.name
            record["message_id"] = message["id"]
            c = classify(record, received)
            record["severity"] = c.severity
            record["reportable"] = c.reportable
            record["report_window_hours"] = c.report_window_hours
            record["ndis_category"] = c.ndis_category
            deadline = c.report_deadline(received)
            record["report_deadline"] = deadline.strftime("%Y-%m-%d %H:%M") if deadline else ""
            record["reasons"] = "; ".join(c.reasons)
            record["status"] = "Open"
            rows.append(record)
        return rows, {"file": name, "status": "processed", "stored_as": stored.name, "records": len(rows)}

    def run_once(self, demo_files=None):
        state = self._load_state()
        processed = set(state["processed_message_ids"])
        since = state["last_received"] or since_iso(self.cfg.lookback_days)

        if demo_files is not None:
            messages = [
                {
                    "id": f"demo-{p.name}",
                    "subject": f"Incident form - {p.stem}",
                    "receivedDateTime": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "from": {"emailAddress": {"address": self.cfg.sender_address}},
                    "_data": p.read_bytes(),
                    "_name": p.name,
                }
                for p in demo_files
            ]
        else:
            messages = self.client.list_messages_from_sender(self.cfg.sender_address, since=since)

        all_rows = []
        stats = {"messages_seen": 0, "messages_new": 0, "attachments": [], "rows": 0}
        for message in messages:
            stats["messages_seen"] += 1
            if self._sender_of(message).lower() != self.cfg.sender_address:
                self._log({"event": "sender_mismatch", "message_id": message["id"], "sender": self._sender_of(message)})
                continue
            if message["id"] in processed:
                continue
            stats["messages_new"] += 1
            if demo_files is not None:
                rows, att_stats = self._ingest_bytes(message, message["_name"], message["_data"])
                stats["attachments"].append(att_stats)
            else:
                rows, att_stats = [], []
                for attachment in self.client.list_attachments(message["id"]):
                    if attachment.get("isInline"):
                        att_stats.append({"file": attachment.get("name", ""), "status": "skipped_inline"})
                        continue
                    data = self.client.download_attachment(message["id"], attachment["id"])
                    r, s = self._ingest_bytes(message, attachment.get("name", "attachment"), data)
                    rows.extend(r)
                    att_stats.append(s)
                stats["attachments"].extend(att_stats)
            all_rows.extend(rows)
            processed.add(message["id"])
            received_raw = message.get("receivedDateTime")
            if received_raw and (state["last_received"] is None or received_raw > state["last_received"]):
                state["last_received"] = received_raw

        state["processed_message_ids"] = sorted(processed)
        self._save_state(state)
        stats["rows"] = len(all_rows)

        register_path = self.cfg.output_dir / REGISTER_NAME
        rows = self._merged_rows(register_path, all_rows)
        write_register(rows, register_path, self.cfg.org_name)
        stats["total_in_register"] = len(rows)
        stats["register"] = str(register_path)
        self._log({"event": "run_complete", **{k: v for k, v in stats.items() if k != "attachments"}})
        return stats

    @staticmethod
    def _dedup_key(row):
        return f"{row.get('source_file', '')}|{row.get('incident_date', '')}|{str(row.get('description', ''))[:120]}"

    def _merged_rows(self, register_path, new_rows):
        merged = {}
        for existing in self._load_register_rows(register_path):
            merged[self._dedup_key(existing)] = existing
        for row in new_rows:
            merged[self._dedup_key(row)] = row
        return list(merged.values())

    def _load_register_rows(self, path):
        path = Path(path)
        if not path.exists():
            return []
        from openpyxl import load_workbook

        wb = load_workbook(path, read_only=True)
        if "Incident Register" not in wb.sheetnames:
            wb.close()
            return []
        ws = wb["Incident Register"]
        rows = list(ws.iter_rows(values_only=True))
        wb.close()
        if len(rows) < 2:
            return []
        headers = [str(h) for h in rows[0]]
        out = []
        for raw in rows[1:]:
            d = dict(zip(headers, raw))
            out.append({
                "incident_date": d.get("Incident Date") or "",
                "received": d.get("Received") or "",
                "subject": d.get("Email Subject") or "",
                "source_file": d.get("Source File") or "",
                "participant": d.get("Participant") or "",
                "location": d.get("Location") or "",
                "incident_type": d.get("Incident Type") or "",
                "ndis_category": d.get("NDIS Category") or None,
                "description": d.get("Description") or "",
                "injuries": d.get("Injuries") or "",
                "actions_taken": d.get("Actions Taken") or "",
                "reported_by": d.get("Reported By") or "",
                "severity": str(d.get("Severity") or "low").lower(),
                "reportable": str(d.get("NDIS Reportable") or "").upper() == "YES",
                "report_window_hours": _parse_window(d.get("Report Window")),
                "report_deadline": d.get("Report Deadline") or "",
                "status": d.get("Status") or "Open",
                "message_id": "",
            })
        return out


def _parse_window(value):
    if not value:
        return None
    digits = "".join(ch for ch in str(value) if ch.isdigit())
    return int(digits) if digits else None


def build_agent(cfg, demo=False):
    client = None if demo else GraphClient(cfg)
    return IncidentAgent(cfg, client)
