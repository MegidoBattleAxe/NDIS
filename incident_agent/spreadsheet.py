from datetime import datetime

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from .classify import SEVERITY_RANK

HEADERS = [
    "Incident Date", "Received", "Email Subject", "Source File", "Participant",
    "Location", "Incident Type", "NDIS Category", "Description", "Injuries",
    "Actions Taken", "Reported By", "Severity", "NDIS Reportable",
    "Report Window", "Report Deadline", "Status",
]

WIDTHS = [16, 20, 34, 34, 22, 20, 22, 34, 60, 30, 40, 20, 12, 16, 14, 20, 12]

HEADER_FILL = PatternFill("solid", fgColor="1F4E78")
HEADER_FONT = Font(color="FFFFFF", bold=True)
REPORTABLE_FILL = PatternFill("solid", fgColor="FFC7CE")
REPORTABLE_FONT = Font(color="9C0006", bold=True)
SEVERITY_STYLE = {
    "critical": ("C00000", "FFFFFF"),
    "high": ("ED7D31", "FFFFFF"),
    "medium": ("FFD966", "000000"),
    "low": (None, None),
}
THIN = Border(*[Side(style="thin", color="BFBFBF")] * 4)
WRAP = Alignment(wrap_text=True, vertical="top")


def _sort_key(row):
    return (-SEVERITY_RANK.get(row["severity"].lower(), 0), str(row.get("incident_date", "")))


def build_workbook(rows, org_name):
    wb = Workbook()
    ws = wb.active
    ws.title = "Incident Register"

    for col, header in enumerate(HEADERS, start=1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(wrap_text=True, vertical="center")
        cell.border = THIN
        ws.column_dimensions[get_column_letter(col)].width = WIDTHS[col - 1]

    for r, row in enumerate(sorted(rows, key=_sort_key), start=2):
        values = [
            row.get("incident_date", ""), row.get("received", ""), row.get("subject", ""),
            row.get("source_file", ""), row.get("participant", ""), row.get("location", ""),
            row.get("incident_type", ""), row.get("ndis_category") or "", row.get("description", ""),
            row.get("injuries", ""), row.get("actions_taken", ""), row.get("reported_by", ""),
            row["severity"].capitalize(), "YES" if row["reportable"] else "No",
            (f"{row['report_window_hours']}h" if row["reportable"] else ""),
            row.get("report_deadline", "") or "", row.get("status", "Open"),
        ]
        for col, value in enumerate(values, start=1):
            cell = ws.cell(row=r, column=col, value=value)
            cell.border = THIN
            cell.alignment = WRAP
            if row["reportable"]:
                cell.fill = REPORTABLE_FILL
                cell.font = REPORTABLE_FONT
        sev = row["severity"].lower()
        bg, fg = SEVERITY_STYLE.get(sev, (None, None))
        if bg:
            sev_cell = ws.cell(row=r, column=13)
            sev_cell.fill = PatternFill("solid", fgColor=bg)
            sev_cell.font = Font(color=fg, bold=True)
            sev_cell.alignment = Alignment(horizontal="center", vertical="top")

    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(HEADERS))}{len(rows) + 1}"

    summary = wb.create_sheet("Summary")
    summary.column_dimensions["A"].width = 40
    summary.column_dimensions["B"].width = 16
    summary["A1"] = f"{org_name} - Incident Register Summary"
    summary["A1"].font = Font(bold=True, size=14)
    summary["A2"] = f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    summary["A4"] = "Total incidents"
    summary["B4"] = len(rows)
    summary["A5"] = "NDIS reportable (highlighted red in register)"
    summary["B5"] = sum(1 for r in rows if r["reportable"])
    summary["B5"].font = Font(color="9C0006", bold=True)
    start = 7
    summary.cell(row=start, column=1, value="Severity").font = Font(bold=True)
    summary.cell(row=start, column=2, value="Count").font = Font(bold=True)
    for i, sev in enumerate(["Critical", "High", "Medium", "Low"], start=start + 1):
        summary.cell(row=i, column=1, value=sev)
        summary.cell(row=i, column=2, value=sum(1 for r in rows if r["severity"].lower() == sev.lower()))
    rep_row = start + 6
    summary.cell(row=rep_row, column=1, value="Reportable source files").font = Font(bold=True)
    for i, r in enumerate([r for r in rows if r["reportable"]], start=rep_row + 1):
        summary.cell(row=i, column=1, value=f"{r.get('source_file', '')} - {r.get('ndis_category', '')}")

    return wb


def write_register(rows, path, org_name):
    wb = build_workbook(rows, org_name)
    wb.save(path)
    return path
