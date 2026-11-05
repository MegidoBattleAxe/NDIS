import make_samples


def test_parse_csv(tmp_path):
    from incident_agent.parsers import parse_attachment

    p = tmp_path / "f.csv"
    make_samples._csv(p, [["Date", "Participant", "Type", "Description"], ["2025-10-02", "J Smith", "Injury", "fell"]])
    rows = parse_attachment(p.name, p.read_bytes())
    assert rows[0]["incident_date"] == "2025-10-02"
    assert rows[0]["participant"] == "J Smith"
    assert rows[0]["incident_type"] == "Injury"


def test_parse_docx(tmp_path):
    from incident_agent.parsers import parse_attachment

    p = tmp_path / "f.docx"
    make_samples.make_docx(p, ["Incident Report", "Date: 2025-10-05 14:40", "Participant: M. Jones", "Description: restraint used without authorisation"])
    rows = parse_attachment(p.name, p.read_bytes())
    assert rows[0]["incident_date"] == "2025-10-05 14:40"
    assert rows[0]["participant"] == "M. Jones"
    assert "restraint" in rows[0]["description"]


def test_parse_pdf(tmp_path):
    from incident_agent.parsers import parse_attachment

    p = tmp_path / "f.pdf"
    make_samples.make_pdf(p, ["Incident Report", "Date: 2025-10-11 08:30", "Type: Abuse", "Description: staff abusing participant"])
    rows = parse_attachment(p.name, p.read_bytes())
    assert rows[0]["incident_type"] == "Abuse"
    assert "abusing" in rows[0]["description"]


def test_parse_json(tmp_path):
    import json

    from incident_agent.parsers import parse_attachment

    p = tmp_path / "f.json"
    p.write_text(json.dumps({"date": "2025-10-09", "participant_name": "K W", "incident_type": "Sexual misconduct", "description": "allegation"}))
    rows = parse_attachment(p.name, p.read_bytes())
    assert rows[0]["participant"] == "K W"
    assert rows[0]["incident_type"] == "Sexual misconduct"


def test_parse_txt_kv(tmp_path):
    from incident_agent.parsers import parse_attachment

    p = tmp_path / "f.txt"
    p.write_text("Date: 2025-10-07\nType: Near miss\nDescription: nearly slipped\n", encoding="utf-8")
    rows = parse_attachment(p.name, p.read_bytes())
    assert rows[0]["incident_type"] == "Near miss"


def test_parse_image_metadata_only(tmp_path):
    from incident_agent.parsers import parse_attachment

    p = tmp_path / "f.png"
    make_samples.make_png(p)
    rows = parse_attachment(p.name, p.read_bytes())
    assert rows[0]["incident_type"] == "photo evidence"
