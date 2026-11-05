from datetime import datetime, timezone

from incident_agent.classify import classify


def test_death_is_critical_reportable_24h():
    c = classify({"incident_type": "Death", "description": "Participant passed away overnight."})
    assert c.severity == "critical"
    assert c.reportable and c.report_window_hours == 24
    assert c.ndis_category == "Death of a participant"


def test_serious_injury_hospitalisation_24h():
    c = classify({"incident_type": "Injury", "description": "Fall, broken wrist, hospitalised for surgery."})
    assert c.reportable and c.report_window_hours == 24
    assert c.severity == "critical"


def test_sexual_misconduct_24h():
    c = classify({"description": "Allegation of sexual misconduct by a visitor."})
    assert c.reportable and c.report_window_hours == 24
    assert c.ndis_category == "Sexual misconduct against a participant"


def test_unauthorised_restrictive_practice_5d():
    c = classify({
        "incident_type": "Restrictive practice",
        "description": "Physical restraint used without authorisation, not in accordance with behaviour support plan.",
    })
    assert c.reportable and c.report_window_hours == 120
    assert c.severity == "high"


def test_near_miss_low_not_reportable():
    c = classify({"incident_type": "Near miss", "description": "Nearly slipped on wet floor, no injury."})
    assert not c.reportable and c.report_window_hours is None
    assert c.severity == "low"


def test_minor_injury_medium():
    c = classify({"description": "Minor bruise from a fall, first aid applied."})
    assert not c.reportable
    assert c.severity == "medium"


def test_explicit_severity_can_raise():
    c = classify({"description": "Something happened.", "severity": "High"})
    assert c.severity == "high"


def test_report_deadline():
    received = datetime(2025, 10, 2, 9, 15, tzinfo=timezone.utc)
    c = classify({"description": "death of participant"}, received)
    deadline = c.report_deadline(received)
    assert deadline is not None and deadline.year == 2025 and deadline.day == 3
