# Security audit — 2026-11-06

Scope: full repo, threat model = email attachments are untrusted; agent reads an
allowlisted sender's mailbox, parses attachments, writes a register. Method: read of
`safety.py`, `graph_client.py`, `parsers.py`, `agent.py`, `config.py`, `.gitignore`,
secret-pattern grep over tracked files, live demo smoke runs. Skill used: `/security-audit`.

## Findings

| Severity | Area | Finding | Evidence | Remediation |
|---|---|---|---|---|
| High | Data integrity | Register/state divergence: if `output/` is deleted but `state.json` kept, already-processed messages are skipped and the register is rebuilt **empty** — silent loss of register rows | `agent.py:71-129` (dedup from state, `_merged_rows` reads existing xlsx); observed in smoke run: `0/6 new messages, register now holds 0 incidents` | If register file is missing while `processed_message_ids` is non-empty, log a `register_divergence` event and warn on console; store register row count in state and alert on mismatch |
| Medium | Attachment parsing | Zip-bomb surface: docx/xlsx are ZIP-based; the 25 MB cap applies to the *compressed* download, decompression can expand far beyond it | `safety.py:41-43` (size cap on raw bytes); `parsers.py:80-91` (`zipfile.ZipFile`, `load_workbook`) | Sum `ZipInfo.file_size` before extraction / use openpyxl `read_only` with a decompressed-size budget; reject archives whose declared uncompressed total exceeds a cap (e.g. 200 MB) |
| Medium | Logging | `parse_failed` writes `str(exc)` into `output/run_log.jsonl`; parser exception messages can embed attachment content snippets | `agent.py:56-58` | Log exception type + message truncated to 200 chars, never raw content |
| Low | Graph query | `$filter` string interpolates `sender.lower()` unencoded; safe today because sender is operator config and is re-checked exactly in code | `graph_client.py:158-166`; `agent.py:96-98` | URL-encode the filter value; keep the in-code exact match |
| Low | Token cache | File is written then `chmod 0600` — brief window with umask-default permissions | `graph_client.py:38-44` | Create with `os.open(path, O_WRONLY|O_CREAT|O_TRUNC, 0o600)` |

## Passed checks (no finding)

- Magic-byte sniffing mapped to extension (`safety.py:46-63`) — renamed executables rejected.
- Empty-file and size-cap checks before sniffing (`safety.py:39-43`).
- Filename sanitisation: `Path(name).name` + `_SAFE_NAME` regex blocks traversal; stored as `<sha256[:16]>_<safe>` and never executed (`safety.py:66-75`).
- Sender allowlist enforced in code as exact case-insensitive match, independent of the Graph filter (`agent.py:96-98`).
- Least-privilege scopes: `Mail.Read`, `User.Read`, `offline_access` only (`graph_client.py:13`).
- `.gitignore` covers `config.env`, `.token_cache.json`, `state.json`, `output/`, `downloads/`, `samples/`; `git grep` for secret patterns found only the `config.example.env` placeholder.
- Token cache written `0600`; 401 triggers single token refresh retry (`graph_client.py:132-137`).
- No `shell=True`, no eval/exec on attachment content, no SQL string building.

## Limitations

- Clone is shallow (5 commits visible); full-history secret scan not possible locally — enable GitHub secret scanning on the repo.

## Verdict

No Critical findings. Demo mode is safe to run. Before/soon-after live mode: fix the
High register-divergence issue and the Medium zip-bomb cap; the Low items can ride
along in a normal PR.

## Remediation status

- High (register/state divergence): **fixed** — `run_once` now warns on stderr and logs
  `register_divergence` / `register_row_count_mismatch` when the register is missing or
  its row count disagrees with `state.json` (which now stores `register_row_count`).
  Covered by `tests/test_register_divergence.py`.
- Medium (zip-bomb cap) and Low items: open.
