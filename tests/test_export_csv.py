import csv
from pathlib import Path

import make_samples
from openpyxl import load_workbook

from incident_agent.agent import IncidentAgent
from incident_agent.config import Config
from incident_agent.spreadsheet import HEADERS, write_register_csv


def _make_cfg(tmp_path):
    return Config(
        output_dir=tmp_path / "output",
        downloads_dir=tmp_path / "downloads",
        state_file=tmp_path / "state.json",
        token_cache=tmp_path / ".token.json",
    )


def _run_demo(tmp_path, export_csv):
    samples = tmp_path / "samples"
    files = make_samples.generate_all(samples)
    agent = IncidentAgent(_make_cfg(tmp_path), export_csv=export_csv)
    return agent.run_once(demo_files=files)


def test_demo_writes_csv_when_enabled(tmp_path):
    stats = _run_demo(tmp_path, export_csv=True)
    csv_path = Path(stats["csv_register"])
    assert csv_path.exists()
    assert csv_path.name == "incident_register.csv"
    with csv_path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.reader(fh))
    assert rows[0] == HEADERS
    assert len(rows) == 7


def test_csv_matches_xlsx_register(tmp_path):
    stats = _run_demo(tmp_path, export_csv=True)
    with Path(stats["csv_register"]).open(newline="", encoding="utf-8") as fh:
        csv_rows = list(csv.reader(fh))
    wb = load_workbook(stats["register"])
    ws = wb["Incident Register"]
    xlsx_rows = [[("" if c is None else str(c)) for c in r] for r in ws.iter_rows(values_only=True)]
    assert csv_rows == xlsx_rows


def test_no_csv_without_flag(tmp_path):
    stats = _run_demo(tmp_path, export_csv=False)
    assert "csv_register" not in stats
    assert not (tmp_path / "output" / "incident_register.csv").exists()


def test_write_register_csv_sorts_like_xlsx(tmp_path):
    rows = [
        {"severity": "low", "incident_date": "2026-01-01", "reportable": False, "status": "Open"},
        {
            "severity": "critical", "incident_date": "2026-01-02", "reportable": True,
            "report_window_hours": 24, "report_deadline": "2026-01-03 10:00",
            "ndis_category": "Death of a participant",
        },
    ]
    path = tmp_path / "r.csv"
    write_register_csv(rows, path)
    with path.open(newline="", encoding="utf-8") as fh:
        out = list(csv.reader(fh))
    assert out[0] == HEADERS
    assert out[1][12] == "Critical"
    assert out[2][12] == "Low"
