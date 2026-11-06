import csv
import io
import json
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape


def make_docx(path, lines):
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        "</Types>"
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
        "</Relationships>"
    )
    paragraphs = "".join(
        f'<w:p><w:r><w:t xml:space="preserve">{escape(line)}</w:t></w:r></w:p>' for line in lines
    )
    document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{paragraphs}</w:body></w:document>"
    )
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("_rels/.rels", rels)
        zf.writestr("word/document.xml", document)


def make_pdf(path, lines):
    def esc(s):
        return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    stream = "\n".join(
        ["BT", "/F1 11 Tf", "14 TL", "50 760 Td"] + [f"({esc(line)}) Tj T*" for line in lines] + ["ET"]
    ).encode("latin-1")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref_pos = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n"
    ).encode()
    Path(path).write_bytes(bytes(out))


def make_png(path):
    import struct
    import zlib

    def chunk(tag, data):
        c = tag + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    raw = zlib.compress(b"\x00\xff\x00\x00")
    Path(path).write_bytes(
        b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", raw) + chunk(b"IEND", b"")
    )


SAMPLES = {
    "incident_2025-001_serious_injury.csv": lambda p: _csv(p, [
        ["Date", "Participant", "Type", "Description", "Injuries", "Actions Taken", "Reported By", "Location"],
        ["2025-10-02 09:15", "J. Smith", "Serious injury",
         "Participant fell from wheelchair during transfer; suspected hip fracture.", "Suspected fractured hip",
         "Ambulance called, hospitalised, family notified.", "A. Nguyen", "Day program - Northside"],
    ]),
    "incident_2025-002_restrictive_practice.docx": lambda p: make_docx(p, [
        "Incident Report",
        "Date: 2025-10-05 14:40",
        "Participant: M. Jones",
        "Type: Restrictive practice",
        "Description: Physical restraint used during behaviour escalation without authorisation and not in accordance with the behaviour support plan.",
        "Restrictive practice: Yes - unauthorised physical restraint, 10 minutes",
        "Actions taken: Incident reported to team leader, BSP review requested.",
        "Reported by: R. Kelly",
        "Location: Group home - Westridge",
    ]),
    "incident_2025-003_near_miss.txt": lambda p: Path(p).write_text(
        "Incident Report\n"
        "Date: 2025-10-07 11:05\n"
        "Participant: T. Brown\n"
        "Type: Near miss\n"
        "Description: Participant nearly slipped on wet floor; no injury occurred. Wet floor sign deployed.\n"
        "Severity: Low\n"
        "Reported by: S. Patel\n"
        "Location: Hallway B\n",
        encoding="utf-8",
    ),
    "incident_2025-004_sexual_misconduct.json": lambda p: Path(p).write_text(
        json.dumps({
            "date": "2025-10-09 16:20",
            "participant": "K. Williams",
            "incident_type": "Sexual misconduct",
            "description": "Allegation of inappropriate sexual contact by a visitor toward a participant. Police notified.",
            "severity": "Critical",
            "actions_taken": "Participant supported, police notified, visitor banned from premises, NDIS Commission notified.",
            "reported_by": "L. Chen",
            "location": "Respite centre - Eastgate",
        }, indent=2),
        encoding="utf-8",
    ),
    "incident_2025-005_abuse.pdf": lambda p: make_pdf(p, [
        "Incident Report",
        "Date: 2025-10-11 08:30",
        "Participant: D. Miller",
        "Type: Abuse",
        "Description: Staff member observed another staff member verbally abusing and pushing a participant.",
        "Injuries: Minor bruise to upper arm",
        "Actions taken: Staff member suspended pending investigation; family and NDIS Commission notified.",
        "Reported by: P. Okafor",
        "Location: Group home - Southside",
    ]),
    "incident_2025-006_photo_evidence.png": lambda p: make_png(p),
}


def _csv(path, rows):
    buf = io.StringIO()
    csv.writer(buf).writerows(rows)
    Path(path).write_text(buf.getvalue(), encoding="utf-8")


def generate_all(directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    for name, maker in SAMPLES.items():
        maker(directory / name)
    return sorted(directory.iterdir())


if __name__ == "__main__":
    import sys

    target = sys.argv[1] if len(sys.argv) > 1 else "samples"
    for f in generate_all(target):
        print(f)
