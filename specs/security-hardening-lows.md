# Spec: close the two Low audit findings

Closes the Low items in `audits/security-audit-2026-11-06.md`.

## Goal

1. **OData filter encoding** (`graph_client.py`): the sender address is interpolated
   into the `$filter` query string unencoded. Encode the query for the URL and escape
   OData string-literal quotes, so a hostile config value cannot break out of the
   filter. The in-code exact sender match in `agent.py` stays as the real control.
2. **Token cache permissions at creation** (`graph_client.py::_save_cache`): create
   the cache file with mode `0600` via `os.open` instead of write-then-`chmod`, so
   there is no window with umask-default permissions. Keep the trailing `chmod` so a
   pre-existing loose file is tightened.

## Requirements

1. `list_messages_from_sender` builds the same logical query, but the request URL is
   percent-encoded (structural chars `$ = & , / ( ) : @` preserved) and any `'` in the
   sender is doubled for the OData literal before encoding.
2. `_save_cache` creates the file with `0600`; a pre-existing file with looser
   permissions ends up `0600` after the call.
3. No behaviour change for normal inputs: same messages returned, same cache contents.

## Non-goals

- Changing Graph scopes or the sender allowlist logic.
- Rotating or encrypting cached tokens.

## Acceptance criteria (tests in `tests/test_graph_client.py`)

- AC1: recorded request URL has no raw spaces/quotes and encodes the sender
  (`%40` etc. allowed). -> `test_filter_url_is_encoded`
- AC2: sender containing `'` appears doubled in the decoded filter.
  -> `test_filter_escapes_odata_quote`
- AC3: fresh cache file mode is exactly `0600`. -> `test_token_cache_created_0600`
- AC4: pre-existing `0644` cache file is `0600` after `_save_cache`.
  -> `test_token_cache_tightens_existing_file`

## Open questions

None.
