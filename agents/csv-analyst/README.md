# csv-analyst

A conversational data analyst agent built with the [Mistral Agents SDK](https://docs.mistral.ai/studio/agents/agents-sdk),
deployed on Mistral Cloud as a managed deployment (`agents deploy`, a Workflows
managed deployment, hardened because the agent acts on behalf of the session user).

You give it a link to a CSV file in your Google Drive and ask questions in plain
language. It retrieves the file through **your** Google Drive connection
(on-behalf-of) and answers with real numbers. The session is stored by Mistral, so
follow-up questions in the same conversation remember the file and everything you
discussed.

## Fixed tools (no arbitrary code execution — the agent runs with `NoSandbox`)

| Tool | What it does |
| --- | --- |
| `search_drive_files` | Find Drive files by name, to turn a file name into a file id/link |
| `load_csv_from_drive` | Download a CSV from Drive (link or file id) via the session user's Google Drive connector, parse it, make it the active dataset |
| `describe_columns` | Per-column inferred type, null/unique counts, min/max/sum or top/sample values |
| `preview_rows` | First rows of the active dataset |
| `filter_rows` | Rows matching ALL conditions (`eq, ne, gt, gte, lt, lte, contains, not_contains, starts_with, ends_with, in, not_in, is_null, not_null, between`) |
| `group_by_aggregate` | Group by columns + `count, count_distinct, sum, avg, min, max, median`, optional filters first |

Inside the tools, Drive is called programmatically with
`get_mistral_client(use_executor_credentials=True).beta.connectors.call_tool_async(...)`
as the session user, so only the read-only connector tools (`search_files`,
`get_file_metadata`, `download_file_content`) are ever used.

## Layout

- `main.py` — the agent (`agent`), its instructions and the fixed tools
- `pyproject.toml` / `uv.lock` — dependencies (`mistralai-agents`)
- `Dockerfile` — the image the managed deployment builds; runs `agents run-worker`

## Develop

```bash
cd agents/csv-analyst
uv sync
uv run agents info                 # what the CLI loads from the project
uv run --env-file .env agents chat # chat locally (needs MISTRAL_API_KEY in .env)
```

## Deploy (Mistral-managed)

```bash
git push origin <branch>           # the deploy builds the pushed commit
uv run --env-file .env agents deploy .   # creates/replaces agent "csv-analyst"
```

The deploy prints a **Vibe Code Web** link (`https://chat.mistral.ai/code?agent=csv-analyst`)
to chat with the deployed agent; sessions also appear under
*Managed Agents > Agent sessions* in Mistral Studio. From any process with a
`MISTRAL_API_KEY`: `agents chat csv-analyst`, or in Python
`agents.Agent.load_from(agent_name="csv-analyst")` + `start_session()`.
