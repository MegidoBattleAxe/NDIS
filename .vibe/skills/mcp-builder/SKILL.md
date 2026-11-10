---
name: mcp-builder
description: "Use when the agent needs live access to an external API, database, or service, for example exposing the incident register or Microsoft Graph to other agents. Guides building a minimal, tested MCP server with a clear, narrowly-scoped tool schema."
license: MIT
compatibility: Requires Python and the MCP SDK
user-invocable: true
allowed-tools:
  - read_file
  - write_file
  - bash
  - grep
---

# MCP builder

Build a small MCP server that gives an agent safe access to one capability. Skills are instructions; MCP servers are tools.

## Workflow

1. Define the single capability (e.g. "read-only query of the incident register", "list unprocessed messages"). One server, few tools.
2. Schema first: for each tool write the name, description, JSON input schema, and output shape. Descriptions must tell the model when to use the tool.
3. Implement with the MCP SDK; keep handlers thin, validate all inputs, and never expose credentials or raw filesystem access.
4. Test each tool directly with a small client script before wiring it into an agent.
5. Document how to add it in Vibe (`config.toml` MCP section) and how to run it.

## Rules

- Read-only by default; any write tool needs an explicit confirmation step.
- No secrets in code or tool descriptions; load from env vars.
- Fail closed: invalid input returns an error message, not a stack trace or partial data.
