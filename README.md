# OpenWebif MCP Server

A Docker-based MCP server for controlling Vu+ and other Enigma2 receivers through
OpenWebif. It exposes OpenWebif features as MCP tools, including EPG search,
timer listing, timer creation, instant recording, zapping, movie listing, and
receiver status checks.

Suggested repository name: `openwebif-mcp-server`.

## Quick Start

Create a local environment file:

```bash
make init
```

Edit `.env` and set at least `OPENWEBIF_BASE_URL` to your receiver's OpenWebif
URL:

```env
OPENWEBIF_BASE_URL=http://192.168.178.50
```

Write actions such as timer creation, zapping, remote-control commands, and TV
messages are disabled by default. Enable them explicitly if you want assistants
to change receiver state:

```env
OPENWEBIF_ALLOW_MUTATIONS=true
```

Start the MCP server:

```bash
make start
```

The default MCP endpoint is:

```text
http://localhost:8000/mcp
```

View logs:

```bash
make logs
```

Stop the service:

```bash
make down
```

## Makefile

The repository is operated through `make`:

```bash
make help
```

Important targets:

- `make init` creates `.env` from `.env.example` if it does not exist yet.
- `make build` builds the Docker image.
- `make up` starts the MCP server in the foreground.
- `make start` starts the MCP server in the background.
- `make logs` follows the service logs.
- `make down` stops and removes the Compose containers.
- `make check` checks Python syntax and validates the Compose configuration.
- `make test-e2e` tests OpenWebif directly and the MCP server end to end.

## MCP Client Configuration

For MCP clients that support Streamable HTTP, configure this server as an HTTP
MCP endpoint:

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

The exact configuration file and schema depend on your MCP client.

## Integration Tests

The end-to-end tests run inside Docker and use your local `.env`.

```bash
make test-e2e
```

This verifies:

- Direct OpenWebif access through `/api/about`, `/api/statusinfo`, and
  `/api/timerlist`.
- The MCP server over Streamable HTTP and JSON-RPC.
- `tools/list` plus the MCP tools `openwebif_about`, `openwebif_status`, and
  `openwebif_timers`.
- Mutation tools are blocked while `OPENWEBIF_ALLOW_MUTATIONS` is disabled.

Run individual test groups:

```bash
make test-e2e-direct
make test-e2e-mcp
```

Optional mutation smoke test:

```bash
make test-e2e-mutation-smoke
```

This test enables `OPENWEBIF_ALLOW_MUTATIONS=true` for the test run and shows a
short message on the receiver. It does not create timers or start recordings.

## Available Tools

- `openwebif_about`, `openwebif_device_info`, `openwebif_status`
- `openwebif_bouquets`, `openwebif_services`
- `openwebif_epg_search`, `openwebif_epg_now_next`
- `openwebif_timers`
- `openwebif_add_timer`, `openwebif_add_timer_by_event_id`
- `openwebif_delete_timer`, `openwebif_toggle_timer`
- `openwebif_record_now`, `openwebif_zap`
- `openwebif_movies`, `openwebif_locations`

## Safety

Do not expose OpenWebif directly to the internet. Keep the receiver and this MCP
server on your local network or behind a VPN.

Mutation tools are disabled by default. Set `OPENWEBIF_ALLOW_MUTATIONS=true`
only when you want assistants to create or delete timers, zap, send receiver
messages, or perform other state-changing actions.

The local `.env` file is not versioned. Do not publish receiver IP addresses,
OpenWebif credentials, or other private network details.

## OpenWebif Notes

OpenWebif returns JSON responses through `/api/<method>`. Timer creation uses
`timeradd` with `sRef`, `begin`, `end`, and `name`; timers from EPG events use
`timeraddbyeventid`.

