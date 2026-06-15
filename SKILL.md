---
name: openwebif-mcp-server
description: Use when an agent needs to control a Vu+/Enigma2 receiver through OpenWebif via MCP - searching EPG, managing timers, zapping channels, starting recordings, or checking receiver status
---

# OpenWebif MCP Server

## Overview

This MCP server exposes OpenWebif API as MCP tools for controlling Vu+ and other Enigma2 receivers. It runs as a Docker container providing Streamable HTTP transport at `http://localhost:8000/mcp`.

All tools are read-only by default. State-changing actions (timers, zap, recordings, messages, remote control) require `OPENWEBIF_ALLOW_MUTATIONS=true`.

## When to Use

- Agent needs to search TV guide / EPG for shows
- Agent needs to list, create, or delete recording timers
- Agent needs to switch channels (zap) on the receiver
- Agent needs to start immediate recordings
- Agent needs to check receiver status (standby, recording, current service)
- Agent needs to list bouquets/services or recordings
- Agent needs to send messages to TV screen or remote control commands

## Quick Reference

| Tool | Purpose | Mutation |
|------|---------|----------|
| `openwebif_about` | Hardware/software info | No |
| `openwebif_device_info` | Device information | No |
| `openwebif_status` | Standby, recording, current service | No |
| `openwebif_current_service` | Currently playing service/event | No |
| `openwebif_bouquets` | List TV/radio bouquets | No |
| `openwebif_services` | List channels for a bouquet | No |
| `openwebif_epg_search` | Search EPG by query string | No |
| `openwebif_epg_now_next` | Now/next EPG for a service | No |
| `openwebif_timers` | List all timers | No |
| `openwebif_add_timer` | Create timer with timestamps | **Yes** |
| `openwebif_add_timer_by_event_id` | Create timer from EPG event ID | **Yes** |
| `openwebif_delete_timer` | Delete timer by sRef/begin/end | **Yes** |
| `openwebif_toggle_timer` | Enable/disable timer | **Yes** |
| `openwebif_record_now` | Start immediate recording | **Yes** |
| `openwebif_zap` | Switch to channel | **Yes** |
| `openwebif_send_message` | Show message on TV | **Yes** |
| `openwebif_remote_control` | Send remote key code | **Yes** |
| `openwebif_movies` | List recordings | No |
| `openwebif_locations` | List recording directories | No |

## Configuration

Required environment variable:
- `OPENWEBIF_BASE_URL` - e.g., `http://192.168.178.50`

Optional:
- `OPENWEBIF_USERNAME` / `OPENWEBIF_PASSWORD` - if OpenWebif has HTTP auth
- `OPENWEBIF_ALLOW_MUTATIONS=true` - enable state-changing tools
- `OPENWEBIF_TIMEOUT=10` - request timeout seconds
- `MCP_HOST=0.0.0.0`, `MCP_PORT=8000` - MCP server bind
- `MCP_ALLOWED_HOSTS` - comma-separated Host allowlist for DNS-rebinding protection (empty = disabled, trusted LAN)

## MCP Client Config

```json
{
  "mcpServers": {
    "openwebif": {
      "transport": "http",
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

## Common Workflows

### Search EPG and create timer
1. `openwebif_epg_search` with query (e.g., "Star Trek")
2. Get `eventid` and `sRef` from results
3. `openwebif_add_timer_by_event_id` with `sRef` and `eventid`

### Zap to channel
1. `openwebif_bouquets` to find bouquet `sRef`
2. `openwebif_services` with bouquet `sRef` to get channel `sRef`
3. `openwebif_zap` with channel `sRef`

### Check what's recording now
1. `openwebif_status` - check `recording` field
2. `openwebif_timers` - list all timers with status

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Mutation tools return error | Set `OPENWEBIF_ALLOW_MUTATIONS=true` in `.env` |
| HTTP 421 from MCP server | Set `MCP_ALLOWED_HOSTS` to client Host header(s) or leave empty for LAN |
| Timer creation fails | Use Unix timestamps for `begin`/`end`; ensure `sRef` from `openwebif_services` |
| Channel not found | `sRef` must match exactly from `openwebif_services` output |
| Connection refused | Verify `OPENWEBIF_BASE_URL` reachable from container (use host IP, not localhost) |

## Running the Server

```bash
make init      # creates .env from .env.example
# edit .env with your receiver IP
make start     # starts in background
make logs      # follow logs
make down      # stop
```

## Testing

```bash
make test-e2e              # full test suite
make test-e2e-direct       # direct OpenWebif API tests
make test-e2e-mcp          # MCP server tests
make test-e2e-mutation-smoke # mutation test (shows message on TV)
```