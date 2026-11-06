"""Conversational CSV data analyst agent (Mistral Agents SDK).

The user shares a Google Drive link to a CSV and asks questions in plain
language. The agent retrieves the file through the session user's Google
Drive connector and answers with real numbers computed by a fixed set of
read-only tools. It has no sandbox, so the model cannot execute code.
"""

from __future__ import annotations

import base64
import csv
import io
import json
import re
from collections import Counter
from typing import Annotated, Any, Literal

from mistralai import agents
from pydantic import BaseModel, Field

DRIVE_CONNECTOR_NAME = "google_drive_mcp"
MAX_FILE_BYTES = 50 * 1024 * 1024
MAX_ROWS = 200_000

OPERATORS = (
    "eq",
    "ne",
    "gt",
    "gte",
    "lt",
    "lte",
    "contains",
    "not_contains",
    "starts_with",
    "ends_with",
    "in",
    "not_in",
    "is_null",
    "not_null",
    "between",
)
AGG_FUNCS = ("count", "count_distinct", "sum", "avg", "min", "max", "median")

_NUMBER_RE = re.compile(r"^[+-]?[0-9]*\.?[0-9]+([eE][+-]?[0-9]+)?$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}([T ]\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:?\d{2})?)?$")
_BOOL_VALUES = {"true", "false", "yes", "no"}


class FilterSpec(BaseModel):
    column: str = Field(description="Column name exactly as in the CSV header.")
    operator: Literal[
        "eq", "ne", "gt", "gte", "lt", "lte", "contains", "not_contains",
        "starts_with", "ends_with", "in", "not_in", "is_null", "not_null", "between",
    ] = Field(description="Comparison operator. 'between' takes value=[low, high]; 'in'/'not_in' take a list; 'is_null'/'not_null' take no value.")
    value: Any = Field(default=None, description="Value to compare against. Number for numeric columns, string otherwise.")


class AggregationSpec(BaseModel):
    column: str = Field(description="Column to aggregate. Use '*' for the row count.")
    func: Literal["count", "count_distinct", "sum", "avg", "min", "max", "median"] = Field(
        description="Aggregation. count/count_distinct work on any column; sum/avg/min/max/median need a numeric column."
    )


class Dataset:
    def __init__(self, columns: list[str], rows: list[dict[str, str | None]]):
        self.columns = columns
        self.rows = rows
        self.types = {c: _infer_type([r.get(c) for r in rows]) for c in columns}


def _norm(v: Any) -> str | None:
    if v is None:
        return None
    s = str(v).strip()
    return s if s != "" else None


def _number(v: Any) -> int | float | None:
    s = _norm(v)
    if s is None or not _NUMBER_RE.match(s):
        return None
    try:
        return int(s)
    except ValueError:
        return float(s)


def _infer_type(values: list[str | None]) -> str:
    vals = [v for v in (_norm(x) for x in values) if v is not None]
    if not vals:
        return "empty"
    if all(v.lower() in _BOOL_VALUES for v in vals):
        return "boolean"
    if all(_DATE_RE.match(v) for v in vals):
        return "date"
    if all(_number(v) is not None for v in vals):
        return "integer" if all(re.fullmatch(r"[+-]?\d+", v) for v in vals) else "float"
    return "text"


def parse_csv_bytes(data: bytes) -> Dataset:
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = data.decode("latin-1")
    if not text.strip():
        raise agents.ToolError("The file is empty.")
    try:
        dialect = csv.Sniffer().sniff(text[:8192], delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel
    reader = csv.reader(io.StringIO(text), dialect)
    raw_rows = [r for r in reader if any((c or "").strip() for c in r)]
    if not raw_rows:
        raise agents.ToolError("The file has no rows.")
    header: list[str] = []
    for h in raw_rows[0]:
        name = (h or "").strip() or f"column_{len(header) + 1}"
        while name in header:
            name = name + "_2"
        header.append(name)
    if len(header) == 1 and not any(d in text.splitlines()[0] for d in ",;\t|"):
        raise agents.ToolError("This does not look like a CSV file (no delimiter found in the first line).")
    rows: list[dict[str, str | None]] = []
    for raw in raw_rows[1:]:
        row: dict[str, str | None] = {}
        for i, name in enumerate(header):
            row[name] = _norm(raw[i]) if i < len(raw) else None
        rows.append(row)
        if len(rows) > MAX_ROWS:
            raise agents.ToolError(f"The CSV has more than {MAX_ROWS} rows; this agent is capped at {MAX_ROWS}.")
    return Dataset(header, rows)


def _eq(a: Any, b: Any) -> bool:
    na, nb = _number(a), _number(b)
    if na is not None and nb is not None:
        return na == nb
    return str(a).lower() == str(b).lower()


def _cmp(a: Any, b: Any) -> int:
    na, nb = _number(a), _number(b)
    if na is not None and nb is not None:
        return (na > nb) - (na < nb)
    sa, sb = str(a), str(b)
    return (sa > sb) - (sa < sb)


def _match(cell: Any, spec: FilterSpec) -> bool:
    v = _norm(cell)
    op = spec.operator
    if op == "is_null":
        return v is None
    if op == "not_null":
        return v is not None
    if v is None:
        return False
    if op in ("in", "not_in"):
        vals = spec.value if isinstance(spec.value, list) else [spec.value]
        hit = any(_eq(v, _norm(x)) for x in vals)
        return hit if op == "in" else not hit
    if op == "between":
        lo, hi = spec.value
        return _cmp(v, lo) >= 0 and _cmp(v, hi) <= 0
    if op in ("eq", "ne"):
        r = _eq(v, _norm(spec.value))
        return r if op == "eq" else not r
    if op in ("gt", "gte", "lt", "lte"):
        c = _cmp(v, _norm(spec.value))
        return {"gt": c > 0, "gte": c >= 0, "lt": c < 0, "lte": c <= 0}[op]
    q = _norm(spec.value)
    if q is None:
        return False
    s, qs = v.lower(), q.lower()
    if op == "contains":
        return qs in s
    if op == "not_contains":
        return qs not in s
    if op == "starts_with":
        return s.startswith(qs)
    if op == "ends_with":
        return s.endswith(qs)
    raise agents.ToolError(f"Unknown operator {op!r}. Use one of: {', '.join(OPERATORS)}.")


def _agg_one(rows: list[dict[str, str | None]], agg: AggregationSpec) -> Any:
    if agg.column == "*":
        if agg.func == "count":
            return len(rows)
        raise agents.ToolError("func must be 'count' when column is '*'.")
    vals = [_norm(r.get(agg.column)) for r in rows]
    if agg.func == "count":
        return sum(v is not None for v in vals)
    if agg.func == "count_distinct":
        return len({v for v in vals if v is not None})
    nums = [n for n in (_number(v) for v in vals) if n is not None]
    if not nums:
        return None
    if agg.func == "sum":
        return sum(nums)
    if agg.func == "avg":
        return sum(nums) / len(nums)
    if agg.func == "min":
        return min(nums)
    if agg.func == "max":
        return max(nums)
    if agg.func == "median":
        ordered = sorted(nums)
        mid = len(ordered) // 2
        return ordered[mid] if len(ordered) % 2 else (ordered[mid - 1] + ordered[mid]) / 2
    raise agents.ToolError(f"Unknown aggregation {agg.func!r}. Use one of: {', '.join(AGG_FUNCS)}.")


def _describe(ds: Dataset, column: str | None) -> list[dict[str, Any]]:
    cols = [column] if column else ds.columns
    if column and column not in ds.columns:
        raise agents.ToolError(f"Column {column!r} is not in this dataset. Columns: {', '.join(ds.columns)}.")
    out: list[dict[str, Any]] = []
    for c in cols:
        vals = [_norm(r.get(c)) for r in ds.rows]
        nonnull = [v for v in vals if v is not None]
        entry: dict[str, Any] = {
            "column": c,
            "type": ds.types[c],
            "rows": len(ds.rows),
            "non_null": len(nonnull),
            "null": len(vals) - len(nonnull),
            "unique": len(set(nonnull)),
        }
        nums = [n for n in (_number(v) for v in nonnull) if n is not None]
        if nums:
            entry["min"] = min(nums)
            entry["max"] = max(nums)
            entry["sum"] = sum(nums)
        elif nonnull:
            entry["top_values"] = [v for v, _ in Counter(nonnull).most_common(5)]
        entry["sample_values"] = nonnull[:5]
        out.append(entry)
    return out


_SESSION_DATA: dict[str, dict[str, tuple[str | None, Dataset]]] = {}


def extract_file_id(link_or_id: str) -> str:
    s = link_or_id.strip()
    m = re.search(r"/d/([A-Za-z0-9_-]{8,})", s) or re.search(r"[?&]id=([A-Za-z0-9_-]{8,})", s)
    if m:
        return m.group(1)
    if re.fullmatch(r"[A-Za-z0-9_-]{8,}", s):
        return s
    raise agents.ToolError(
        "No Google Drive file id found in that input. Paste a full Drive link "
        "(https://drive.google.com/file/d/<id>/view?...) or the file id itself."
    )


async def _drive_call(tool_name: str, arguments: dict[str, Any]) -> Any:
    from mistralai.workflows.client import get_mistral_client

    errors: list[str] = []
    for use_executor in (True, False):
        try:
            client = get_mistral_client(use_executor_credentials=use_executor)
            resp = await client.beta.connectors.call_tool_async(
                connector_id_or_name=DRIVE_CONNECTOR_NAME,
                tool_name=tool_name,
                arguments=arguments,
            )
        except agents.ToolError:
            raise
        except Exception as e:
            errors.append(type(e).__name__)
            continue
        texts = [t for t in (getattr(b, "text", None) for b in (resp.content or [])) if t]
        blob = "\n".join(texts)
        try:
            return json.loads(blob)
        except (json.JSONDecodeError, TypeError):
            return blob
    raise agents.ToolError(
        f"Google Drive call {tool_name!r} failed ({', '.join(errors) or 'unknown error'}). "
        "Make sure the Google Drive connector is connected for this user at "
        "console.mistral.ai/build/connectors, then try again."
    )


async def _load_dataset(ctx: agents.ToolCallbackContext, link_or_id: str) -> tuple[str, Dataset, dict[str, Any]]:
    file_id = extract_file_id(link_or_id)
    meta = await _drive_call("get_file_metadata", {"file_id": file_id})
    if not isinstance(meta, dict) or not meta.get("id"):
        raise agents.ToolError(
            f"Drive file {file_id!r} was not found or is not shared with you. "
            "Check the link, or call search_drive_files to find the file by name."
        )
    modified = meta.get("modified_time")
    try:
        size = int(meta.get("file_size") or 0)
    except (TypeError, ValueError):
        size = 0
    if size > MAX_FILE_BYTES:
        raise agents.ToolError(f"The file is {size} bytes; the limit is {MAX_FILE_BYTES} bytes.")
    cache = _SESSION_DATA.setdefault(ctx.session.id, {})
    cached = cache.get(file_id)
    if cached is not None and cached[0] == modified:
        return file_id, cached[1], meta
    dl = await _drive_call("download_file_content", {"file_id": file_id})
    payload: Any = dl
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError:
            pass
    data: bytes | None = None
    if isinstance(payload, dict) and payload.get("content"):
        try:
            data = base64.b64decode(payload["content"], validate=True)
        except Exception:
            data = str(payload["content"]).encode()
    elif isinstance(payload, str):
        data = payload.encode()
    if data is None:
        raise agents.ToolError(f"Could not download the content of Drive file {file_id!r}.")
    ds = parse_csv_bytes(data)
    cache[file_id] = (modified, ds)
    return file_id, ds, meta


def _resolve(ctx: agents.ToolCallbackContext, file_id: str | None) -> tuple[str, Dataset]:
    cache = _SESSION_DATA.get(ctx.session.id, {})
    if file_id is None:
        if len(cache) == 1:
            fid, (_, ds) = next(iter(cache.items()))
            return fid, ds
        if not cache:
            raise agents.ToolError(
                "No CSV is loaded in this session yet. Call load_csv_from_drive with the "
                "Drive link or file id from this conversation (or search_drive_files to find it by name)."
            )
        raise agents.ToolError(
            f"Several datasets are loaded ({', '.join(cache)}). Pass file_id to choose one."
        )
    if file_id not in cache:
        raise agents.ToolError(
            f"Dataset {file_id!r} is not in this session's cache (the worker may have restarted). "
            "Call load_csv_from_drive with that file id or Drive link to reload it."
        )
    return file_id, cache[file_id][1]


def _check_columns(ds: Dataset, columns: list[str]) -> None:
    missing = [c for c in columns if c not in ds.columns]
    if missing:
        raise agents.ToolError(f"Column(s) {missing} not in this dataset. Columns: {', '.join(ds.columns)}.")


@agents.tool
async def search_drive_files(
    ctx: agents.ToolCallbackContext,
    /,
    query: Annotated[str, Field(description="Drive query, e.g. \"title contains 'receipts' and mimeType = 'text/csv'\".")],
    page_size: int = 10,
) -> dict:
    """Search the session user's Google Drive for files, to turn a file name into a file id. Read-only."""
    res = await _drive_call("search_files", {"query": query, "page_size": page_size})
    files = res.get("files") if isinstance(res, dict) else None
    if files is None:
        raise agents.ToolError(f"Unexpected search result: {str(res)[:300]}")
    return {
        "files": [
            {
                "id": f.get("id"),
                "title": f.get("title"),
                "mime_type": f.get("mime_type"),
                "size_bytes": f.get("file_size"),
                "modified_time": f.get("modified_time"),
                "view_url": f.get("view_url"),
            }
            for f in files
        ],
        "next_page_token": res.get("next_page_token") if isinstance(res, dict) else None,
    }


@agents.tool
async def load_csv_from_drive(
    ctx: agents.ToolCallbackContext,
    /,
    drive_link_or_id: Annotated[str, Field(description="Full Google Drive link (https://drive.google.com/file/d/<id>/view?...) or a bare Drive file id.")],
) -> dict:
    """Download a CSV from the session user's Google Drive through their Google Drive connection, parse it, and make it the active dataset of this conversation. Returns file_id, title, size, row_count, column_count and columns."""
    file_id, ds, meta = await _load_dataset(ctx, drive_link_or_id)
    return {
        "file_id": file_id,
        "title": meta.get("title"),
        "mime_type": meta.get("mime_type"),
        "size_bytes": meta.get("file_size"),
        "modified_time": meta.get("modified_time"),
        "row_count": len(ds.rows),
        "column_count": len(ds.columns),
        "columns": ds.columns,
    }


@agents.tool
async def describe_columns(
    ctx: agents.ToolCallbackContext,
    /,
    file_id: Annotated[str | None, Field(description="Drive file id of the dataset. Omit when only one dataset is loaded in this session.")] = None,
    column: Annotated[str | None, Field(description="Describe only this column. Omit for all columns.")] = None,
) -> dict:
    """Describe the columns of the loaded CSV: inferred type, null/unique counts, min/max/sum for numeric columns, top and sample values for text columns."""
    fid, ds = _resolve(ctx, file_id)
    return {"file_id": fid, "columns": _describe(ds, column)}


@agents.tool
async def preview_rows(
    ctx: agents.ToolCallbackContext,
    /,
    file_id: Annotated[str | None, Field(description="Drive file id of the dataset. Omit when only one dataset is loaded in this session.")] = None,
    limit: int = 20,
) -> dict:
    """Return the first rows of the loaded CSV, as raw values, to see concrete data."""
    fid, ds = _resolve(ctx, file_id)
    limit = max(1, min(limit, 200))
    return {"file_id": fid, "row_count": len(ds.rows), "columns": ds.columns, "rows": ds.rows[:limit], "truncated": len(ds.rows) > limit}


@agents.tool
async def filter_rows(
    ctx: agents.ToolCallbackContext,
    /,
    conditions: Annotated[list[FilterSpec], Field(description="All conditions must match (AND).")],
    file_id: Annotated[str | None, Field(description="Drive file id of the dataset. Omit when only one dataset is loaded in this session.")] = None,
    limit: int = 50,
) -> dict:
    """Return rows of the loaded CSV matching ALL given conditions. Also returns total_matches so the model can report full counts."""
    fid, ds = _resolve(ctx, file_id)
    _check_columns(ds, [c.column for c in conditions])
    matched = [r for r in ds.rows if all(_match(r.get(c.column), c) for c in conditions)]
    limit = max(1, min(limit, 500))
    return {
        "file_id": fid,
        "total_matches": len(matched),
        "returned": min(limit, len(matched)),
        "columns": ds.columns,
        "rows": matched[:limit],
    }


@agents.tool
async def group_by_aggregate(
    ctx: agents.ToolCallbackContext,
    /,
    group_by: Annotated[list[str], Field(description="Column(s) to group by.")],
    aggregations: Annotated[list[AggregationSpec], Field(description="Aggregations to compute per group.")],
    filters: Annotated[list[FilterSpec] | None, Field(description="Optional conditions; only matching rows are aggregated.")] = None,
    file_id: Annotated[str | None, Field(description="Drive file id of the dataset. Omit when only one dataset is loaded in this session.")] = None,
    limit: int = 100,
) -> dict:
    """Group rows of the loaded CSV by one or more columns and compute aggregates (count, count_distinct, sum, avg, min, max, median) per group."""
    fid, ds = _resolve(ctx, file_id)
    _check_columns(ds, group_by + [c.column for c in (filters or []) if c.column != "*"] + [a.column for a in aggregations if a.column != "*"])
    rows = ds.rows
    if filters:
        rows = [r for r in rows if all(_match(r.get(c.column), c) for c in filters)]
    buckets: dict[tuple, list[dict[str, str | None]]] = {}
    order: list[tuple] = []
    for r in rows:
        key = tuple(_norm(r.get(g)) for g in group_by)
        if key not in buckets:
            buckets[key] = []
            order.append(key)
        buckets[key].append(r)
    out: list[dict[str, Any]] = []
    for key in order:
        row: dict[str, Any] = dict(zip(group_by, key))
        for agg in aggregations:
            row[f"{agg.func}({agg.column})"] = _agg_one(buckets[key], agg)
        out.append(row)
    first_agg = f"{aggregations[0].func}({aggregations[0].column})" if aggregations else None
    if first_agg and all(_number(r.get(first_agg)) is not None for r in out):
        out.sort(key=lambda r: _number(r[first_agg]), reverse=True)
    else:
        out.sort(key=lambda r: tuple(str(v) for v in r.values()))
    limit = max(1, min(limit, 1000))
    return {
        "file_id": fid,
        "rows_in_scope": len(rows),
        "total_groups": len(out),
        "returned": min(limit, len(out)),
        "groups": out[:limit],
    }


INSTRUCTIONS = """You are a conversational data analyst. The user points you to a CSV file in their Google Drive and asks questions about it in plain language. Answer with real numbers computed from the file, never invented ones. You have a fixed set of read-only tools and no code execution.

Tools:
- search_drive_files: find files in the user's Drive by name (query like "title contains 'receipts' and mimeType = 'text/csv'").
- load_csv_from_drive: download a CSV from Drive by link or file id and make it the active dataset of this conversation. Returns file_id, title, row_count, column_count, columns.
- describe_columns: per-column inferred type, null/unique counts, min/max/sum (numeric) or top/sample values (text).
- preview_rows: the first rows of the active dataset.
- filter_rows: rows matching ALL given conditions. Operators: eq, ne, gt, gte, lt, lte, contains, not_contains, starts_with, ends_with, in, not_in, is_null, not_null, between.
- group_by_aggregate: group by one or more columns and compute count, count_distinct, sum, avg, min, max, median, with optional filters applied first.

How to work:
1. If the user gives a Drive link or file id, call load_csv_from_drive with it. If they only name the file, call search_drive_files first, then load the matching file.
2. Remember the file_id and link for the whole conversation and reuse them in every later tool call (pass file_id, or omit it when only one dataset is loaded). Never ask the user to repeat the link. If a tool reports that the dataset is not loaded (for example after a worker restart), call load_csv_from_drive again with the remembered link or file id.
3. Never compute numbers yourself from raw CSV text, and do not call the google_drive_mcp connector tools directly: retrieve files only with search_drive_files / load_csv_from_drive, and analyze only with describe_columns, preview_rows, filter_rows and group_by_aggregate. If load_csv_from_drive fails, report the exact tool error to the user instead of improvising. Before answering, call describe_columns, and preview_rows when you need concrete values, so you use the real column names. Compute answers with filter_rows and group_by_aggregate, chaining calls when needed (e.g. filter, then aggregate the filtered rows with filters=).
4. Reply concisely in Markdown: restate the question briefly, give the numbers (a small table when helpful), and name the file and columns they come from. If the tools cannot answer something, say exactly what is missing instead of guessing.
5. Follow-up questions refer to the same loaded file unless the user says otherwise. If the user shares a new link, load it and use that dataset from then on.
"""

agent = agents.Agent(
    model="mistral-large-4",
    name="csv-analyst",
    instructions=INSTRUCTIONS,
    tools=[
        search_drive_files,
        load_csv_from_drive,
        describe_columns,
        preview_rows,
        filter_rows,
        group_by_aggregate,
    ],
    connectors=[agents.connector(DRIVE_CONNECTOR_NAME)],
)
