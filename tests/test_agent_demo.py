import json
from pathlib import Path

import make_samples
from openpyxl import load_workbook

from incident_agent.agent import IncidentAgent
from incident_agent.config import Config


def _make_cfg(tmp_path):
    return Config(
        output_dir=tmp_path / "output",
        downloads_dir=tmp_path / "downloads",
        state_file=tmp_path / "state.json",
        token_cache=tmp_path / ".token.json",
    )


def test_demo_end_to_end(tmp_path):
    samples = tmp_path / "samples"
    files = make_samples.generate_all(samples)
    agent = IncidentAgent(_make_cfg(tmp_path))
    stats = agent.run_once(demo_files=files)

    assert stats["messages_new"] == len(files)
    register = Path(stats["register"])
    assert register.exists()

    wb = load_workbook(register)
    ws = wb["Incident Register"]
    rows = list(ws.iter_rows(min_row=2, values_only=False))
    assert len(rows) == 6

    header = [c.value for c in ws[1]]
    sev_col = header.index("Severity") + 1
    rep_col = header.index("NDIS Reportable") + 1
    sev_values = [r[sev_col - 1].value for r in rows]
    assert sev_values[0] in ("Critical", "High")

    reportable = [r for r in rows if r[rep_col - 1].value == "YES"]
    assert len(reportable) == 4
    for r in reportable:
        fill = r[0].fill
        assert fill.fgColor.rgb in ("00FFC7CE", "FFC7CE")
        assert r[0].font.color.rgb in ("009C0006", "FF9C0006")

    non_reportable = [r for r in rows if r[rep_col - 1].value == "No"]
    assert len(non_reportable) == 2

    summary = wb["Summary"]
    assert summary["B4"].value == 6
    assert summary["B5"].value == 4

    state = json.loads((tmp_path / "state.json").read_text())
    assert len(state["processed_message_ids"]) == len(files)

    downloaded = list((tmp_path / "downloads").iterdir())
    assert len(downloaded) == len(files)

    log = (tmp_path / "output" / "run_log.jsonl").read_text().splitlines()
    assert any('"run_complete"' in line for line in log)


def test_demo_is_idempotent(tmp_path):
    samples = tmp_path / "samples"
    files = make_samples.generate_all(samples)
    cfg = _make_cfg(tmp_path)
    agent = IncidentAgent(cfg)
    agent.run_once(demo_files=files)
    stats = agent.run_once(demo_files=files)
    assert stats["messages_new"] == 0
    assert stats["total_in_register"] == 6


def test_rejects_malicious_attachment_in_demo(tmp_path):
    samples = tmp_path / "samples"
    samples.mkdir()
    (samples / "invoice.pdf").write_bytes(b"MZ\x90\x00\x03\x00\x00\x00 exe bytes")
    (samples / "notes.txt").write_text("Date: 2025-10-07\nType: Near miss\nDescription: slipped\n", encoding="utf-8")
    agent = IncidentAgent(_make_cfg(tmp_path))
    stats = agent.run_once(demo_files=sorted(samples.iterdir()))
    statuses = {a["file"]: a["status"] for a in stats["attachments"]}
    assert statuses["invoice.pdf"] == "rejected"
    assert statuses["notes.txt"] == "processed"
    assert stats["rows"] == 1
