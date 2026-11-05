from incident_agent.safety import store_attachment, validate_attachment


def test_accepts_valid_pdf():
    ok, reason = validate_attachment("form.pdf", b"%PDF-1.4\n...", 1024)
    assert ok, reason


def test_accepts_valid_docx_zip():
    ok, reason = validate_attachment("form.docx", b"PK\x03\x04rest", 1024)
    assert ok, reason


def test_accepts_text():
    ok, reason = validate_attachment("form.csv", "a,b\n1,2\n".encode(), 1024)
    assert ok, reason


def test_rejects_exe_extension():
    ok, reason = validate_attachment("invoice.exe", b"MZ\x90\x00", 1024)
    assert not ok


def test_rejects_disguised_executable():
    ok, reason = validate_attachment("invoice.pdf", b"MZ\x90\x00\x03\x00", 1024)
    assert not ok
    assert "executable" in reason or "sniffed" in reason


def test_rejects_oversize():
    ok, reason = validate_attachment("big.pdf", b"%PDF-" + b"x" * 2000, 1024)
    assert not ok
    assert "exceeds" in reason


def test_rejects_empty():
    ok, _ = validate_attachment("empty.txt", b"", 1024)
    assert not ok


def test_store_attachment_uses_hash_prefix(tmp_path):
    path = store_attachment(tmp_path, "../evil name.pdf", b"%PDF-1.4 x")
    assert path.parent == tmp_path
    assert "/" not in path.name and ".." not in path.name
    assert path.name.endswith("_evil_name.pdf")
