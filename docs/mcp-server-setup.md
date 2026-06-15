# AKC MCP Server — Setup

One MCP server wraps the AKC REST API, so **the same tools work in Claude Code, Claude Desktop, Codex, and Gemini CLI**. This is the universal *tool* layer (data-plane verbs). The *judgment* layer — when to recall/remember — lives in each client's instruction file (`.claude/skills/`, `AGENTS.md`, `GEMINI.md`).

> Control-plane curation (promote/audit/gaps) is **not** here — that is OpenClaw's Steward role, which calls AKC directly. The MCP server is for end users only.

## Tools

| Tool | Calls | Purpose |
|------|-------|---------|
| `akc_recall` | `POST /recall` | Fetch confidence-ranked patterns before a task |
| `akc_remember` | `POST /remember` | Record an outcome after a task (async distill) |
| `akc_stats` | `GET /stats` | KB health: tier counts, hit-rate |
| `akc_export` | `POST /kb/export` | Markdown sheet of Gold+Production patterns |
| `akc_health` | `GET /health` | Liveness + pattern count |

## 1. Install

```bash
python3 -m venv ~/.akc-mcp-venv
~/.akc-mcp-venv/bin/pip install mcp httpx
```

Note the two absolute paths you'll reuse below:
- **Python**: `~/.akc-mcp-venv/bin/python`
- **Server**: `<repo>/mcp/server.py`
- **Endpoint**: `AKC_ENDPOINT=https://endpoint-30123c53-b859-4599-a339-94b2cedabf7b.agentbase-runtime.aiplatform.vngcloud.vn`

## 2. Configure your client

### Claude Code

```bash
claude mcp add akc \
  --env AKC_ENDPOINT=https://endpoint-30123c53-b859-4599-a339-94b2cedabf7b.agentbase-runtime.aiplatform.vngcloud.vn \
  -- ~/.akc-mcp-venv/bin/python <repo>/mcp/server.py
```

Or commit a project `.mcp.json`:

```json
{
  "mcpServers": {
    "akc": {
      "command": "~/.akc-mcp-venv/bin/python",
      "args": ["<repo>/mcp/server.py"],
      "env": { "AKC_ENDPOINT": "https://endpoint-30123c53-b859-4599-a339-94b2cedabf7b.agentbase-runtime.aiplatform.vngcloud.vn" }
    }
  }
}
```

### Claude Desktop

Edit `claude_desktop_config.json` (Settings → Developer → Edit Config):

```json
{
  "mcpServers": {
    "akc": {
      "command": "/Users/you/.akc-mcp-venv/bin/python",
      "args": ["/abs/path/dl_starter_kit/mcp/server.py"],
      "env": { "AKC_ENDPOINT": "https://endpoint-30123c53-b859-4599-a339-94b2cedabf7b.agentbase-runtime.aiplatform.vngcloud.vn" }
    }
  }
}
```

### Codex CLI

Add to `~/.codex/config.toml`:

```toml
[mcp_servers.akc]
command = "/Users/you/.akc-mcp-venv/bin/python"
args = ["/abs/path/dl_starter_kit/mcp/server.py"]
env = { AKC_ENDPOINT = "https://endpoint-30123c53-b859-4599-a339-94b2cedabf7b.agentbase-runtime.aiplatform.vngcloud.vn" }
```

### Gemini CLI

Add to `~/.gemini/settings.json`:

```json
{
  "mcpServers": {
    "akc": {
      "command": "/Users/you/.akc-mcp-venv/bin/python",
      "args": ["/abs/path/dl_starter_kit/mcp/server.py"],
      "env": { "AKC_ENDPOINT": "https://endpoint-30123c53-b859-4599-a339-94b2cedabf7b.agentbase-runtime.aiplatform.vngcloud.vn" }
    }
  }
}
```

## 3. Verify

Restart the client, then ask: *"Use akc_health to check the knowledge base."* Expect `status=ok pattern_count=34`. Then *"akc_recall for a Japan casual-game keyword launch"* should return the HERO kanji-keyword pattern.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `AKC_ENDPOINT env var is not set` | Add `env` block with the endpoint to the client config |
| Tool not listed | Use the venv python's **absolute** path; restart the client fully |
| Timeout on recall | First semantic call is slow (Memory Service warmup); raise `AKC_TIMEOUT` |
