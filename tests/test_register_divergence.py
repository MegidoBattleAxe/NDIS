import json
from pathlib import Path

import make_samples

from incident_agent.agent import IncidentAgent
from incident_agent.config import Config


def _make_cfg(tmp_path):
    return Config(
        output_dir=tmp_path / "output",
        downloads_dir=tmp_path / "downloads",
        state_file=tmp_path / "state.json",
        token_cache=tmp_path / ".token.json",
    )


def _run_demo(tmp_path, capsys=None):
    samples = tmp_path / "samples"
    files = make_samples.generate_all(samples)
    agent = IncidentAgent(_make_cfg(tmp_path))
    stats = agent.run_once(demo_files=files)
    return agent, stats


def _run_log_events(tmp_path):
    log = tmp_path / "output" / "run_log.jsonl"
    return [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()]


def test_warns_when_register_missing(tmp_path, capsys):
    _, stats = _run_demo(tmp_path)
    assert stats["total_in_register"] == 6
    Path(stats["register"]).unlink()

    _, stats2 = _run_demo(tmp_path)
    captured = capsys.readouterr()
    assert "WARNING" in captured.err
    assert "register_divergence" in captured.err or "missing" in captured.err
    events = [e["event"] for e in _run_log_events(tmp_path)]
    assert "register_divergence" in events
    assert stats2["total_in_register"] == 0


def test_quiet_when_consistent(tmp_path, capsys):
    _run_demo(tmp_path)
    _run_demo(tmp_path)
    captured = capsys.readouterr()
    assert "WARNING" not in captured.err
    events = [e["event"] for e in _run_log_events(tmp_path)]
    assert "register_divergence" not in events
    assert "register_row_count_mismatch" not in events


def test_state_records_register_row_count(tmp_path):
    _run_demo(tmp_path)
    state = json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))
    assert state["register_row_count"] == 6


def test_warns_on_row_count_mismatch(tmp_path, capsys):
    _run_demo(tmp_path)
    state_path = tmp_path / "state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["register_row_count"] = 999
    state_path.write_text(json.dumps(state), encoding="utf-8")

    _run_demo(tmp_path)
    captured = capsys.readouterr()
    assert "WARNING" in captured.err
    events = [e["event"] for e in _run_log_events(tmp_path)]
    assert "register_row_count_mismatch" in events
