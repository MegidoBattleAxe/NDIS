import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta

SEVERITY_RANK = {"low": 1, "medium": 2, "high": 3, "critical": 4}

NDIS_REPORTABLE_24H = {
    "Death of a participant": ["death", "deceased", "died", "passed away", "fatal", "life-threatening"],
    "Serious injury of a participant": [
        "serious injury", "fracture", "broken bone", "head injury", "brain injury",
        "hospitalis", "hospitaliz", "ambulance", "emergency department", "surgery",
        "unconscious", "seizure", "choking", "significant bleeding", "burn",
    ],
    "Abuse of a participant": ["abuse", "assault", "exploitation", "financial abuse", "domestic violence", "stalking"],
    "Neglect of a participant": [
        "neglect", "malnutrition", "dehydration", "pressure injury", "pressure ulcer",
        "medication error", "missed medication", "wrong medication", "unmet care needs",
    ],
    "Sexual misconduct against a participant": [
        "sexual misconduct", "sexual assault", "rape", "grooming", "inappropriate sexual",
        "sexual harassment", "indecent assault",
    ],
    "Unlawful contact with a participant": ["unlawful contact", "unauthorised restraint", "police involved", "charged with", "criminal offence"],
}

NDIS_REPORTABLE_5D = {
    "Unauthorised use of a restrictive practice": [
        "restrictive practice", "restraint", "seclusion", "chemical restraint",
        "physical restraint", "not in accordance with", "without authorisation",
        "without authorization", "behaviour support plan", "behavior support plan",
    ],
}

INJURY_ONLY_KEYWORDS = ["injury", "bruise", "cut", "sprain", "minor fall", "first aid"]


@dataclass
class Classification:
    severity: str
    reportable: bool
    report_window_hours: int | None
    ndis_category: str | None
    reasons: list = field(default_factory=list)

    def report_deadline(self, received):
        if not self.reportable or received is None:
            return None
        return received + timedelta(hours=self.report_window_hours)


def _match_categories(text, table):
    hits = {}
    for category, keywords in table.items():
        for kw in keywords:
            if kw in text:
                hits.setdefault(category, []).append(kw)
                break
    return hits


def classify(record, received=None):
    text_parts = [
        record.get("incident_type", ""),
        record.get("description", ""),
        record.get("injuries", ""),
        record.get("actions_taken", ""),
        record.get("restrictive_practice", ""),
    ]
    text = " ".join(text_parts).lower()
    text = re.sub(r"\b(no|without)\s+(injury|injuries|harm|hurt)\b", " ", text)

    hits_24h = _match_categories(text, NDIS_REPORTABLE_24H)
    hits_5d = _match_categories(text, NDIS_REPORTABLE_5D)

    explicit = record.get("severity", "").strip().lower()
    explicit_rank = SEVERITY_RANK.get(explicit, 0)

    reasons = []
    if hits_24h:
        computed = "critical"
        reportable, window, category = True, 24, next(iter(hits_24h))
        reasons.append(f"matches NDIS reportable incident (24h): {category} via {hits_24h[category]}")
    elif hits_5d:
        computed = "high"
        reportable, window, category = True, 120, next(iter(hits_5d))
        reasons.append(f"matches NDIS reportable incident (5 days): {category} via {hits_5d[category]}")
    elif any(kw in text for kw in INJURY_ONLY_KEYWORDS):
        computed = "medium"
        reportable, window, category = False, None, None
        reasons.append("injury-type event, no 24h/5d reportable category matched")
    else:
        computed = "low"
        reportable, window, category = False, None, None
        reasons.append("no reportable category matched")

    severity = max((computed, explicit), key=lambda s: SEVERITY_RANK.get(s, 0)) if explicit in SEVERITY_RANK else computed
    if explicit in SEVERITY_RANK and SEVERITY_RANK[explicit] > SEVERITY_RANK[computed]:
        reasons.append(f"severity raised to {explicit} by explicit field in form")

    return Classification(
        severity=severity,
        reportable=reportable,
        report_window_hours=window,
        ndis_category=category if reportable else None,
        reasons=reasons,
    )


def parse_received(value):
    if isinstance(value, datetime):
        return value
    if not value:
        return None
    text = str(value).strip().replace("Z", "+00:00")
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d %H:%M:%S%z", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y %H:%M", "%d/%m/%Y"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None
