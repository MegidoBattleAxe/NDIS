import hashlib
import io
import re
import zipfile
from pathlib import Path

ARCHIVE_EXPANSION_LIMIT = 10

ALLOWED_EXTENSIONS = {
    ".pdf", ".docx", ".xlsx", ".csv", ".txt", ".json",
    ".png", ".jpg", ".jpeg",
}

TEXT_EXTENSIONS = {".csv", ".txt", ".json"}

_ZIP_MAGIC = b"PK\x03\x04"
_PDF_MAGIC = b"%PDF-"
_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
_JPG_MAGIC = b"\xff\xd8\xff"

_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


def archive_declared_bytes(data):
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            return sum(info.file_size for info in zf.infolist())
    except (zipfile.BadZipFile, OSError, ValueError):
        return None


def sniff_kind(data):
    if data.startswith(_PDF_MAGIC):
        return ".pdf"
    if data.startswith(_ZIP_MAGIC):
        return ".zip"
    if data.startswith(_PNG_MAGIC):
        return ".png"
    if data.startswith(_JPG_MAGIC):
        return ".jpg"
    try:
        data.decode("utf-8")
        return ".text"
    except UnicodeDecodeError:
        return None


def validate_attachment(name, data, max_bytes):
    ext = Path(name).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return False, f"extension {ext or '(none)'} not in allowlist"
    if len(data) == 0:
        return False, "empty attachment"
    if len(data) > max_bytes:
        return False, f"size {len(data)} exceeds limit {max_bytes}"
    kind = sniff_kind(data)
    if kind is None:
        return False, "unrecognised binary content (possible executable)"
    expected = {
        ".pdf": {".pdf"},
        ".docx": {".zip"},
        ".xlsx": {".zip"},
        ".csv": {".text"},
        ".txt": {".text"},
        ".json": {".text"},
        ".png": {".png"},
        ".jpg": {".jpg"},
        ".jpeg": {".jpg"},
    }[ext]
    if kind not in expected:
        return False, f"content does not match extension {ext} (sniffed {kind})"
    if kind == ".zip":
        declared = archive_declared_bytes(data)
        if declared is None:
            return False, "corrupt zip archive"
        limit = max_bytes * ARCHIVE_EXPANSION_LIMIT
        if declared > limit:
            return False, f"archive declares {declared} uncompressed bytes, exceeds limit {limit}"
    return True, "ok"


def sanitize_name(name):
    base = Path(name).name
    cleaned = _SAFE_NAME.sub("_", base)
    return cleaned[:120] or "attachment"


def store_attachment(downloads_dir, name, data):
    downloads_dir = Path(downloads_dir)
    downloads_dir.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(data).hexdigest()[:16]
    safe = sanitize_name(name)
    path = downloads_dir / f"{digest}_{safe}"
    path.write_bytes(data)
    return path
