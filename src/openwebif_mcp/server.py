from __future__ import annotations

import os
from typing import Annotated, Any

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from .openwebif import OpenWebifClient, OpenWebifConfig


mcp = FastMCP("OpenWebif MCP", stateless_http=True, json_response=True)
client = OpenWebifClient(OpenWebifConfig.from_env())


def _ok(payload: Any) -> Any:
    return payload


@mcp.tool()
def openwebif_about() -> Any:
    """Return OpenWebif hardware, software, and currently running service information."""
    return _ok(client.api("about"))


@mcp.tool()
def openwebif_device_info() -> Any:
    """Return receiver device information."""
    return _ok(client.api("deviceinfo"))


@mcp.tool()
def openwebif_status() -> Any:
    """Return receiver status information such as standby, recording, and current service."""
    return _ok(client.api("statusinfo"))


@mcp.tool()
def openwebif_current_service() -> Any:
    """Return the currently playing service and event."""
    return _ok(client.api("getcurrent"))


@mcp.tool()
def openwebif_bouquets() -> Any:
    """List TV/radio bouquets from OpenWebif."""
    return _ok(client.api("bouquets"))


@mcp.tool()
def openwebif_services(
    service_ref: Annotated[
        str,
        Field(description="Bouquet or parent service reference returned by openwebif_bouquets."),
    ],
) -> Any:
    """List services/channels for a bouquet or parent service reference."""
    return _ok(client.api("getservices", {"sRef": service_ref}))


@mcp.tool()
def openwebif_epg_search(
    query: Annotated[str, Field(description="Search term, e.g. movie or show title.")],
) -> Any:
    """Search the receiver EPG for matching events."""
    return _ok(client.api("epgsearch", {"search": query}))


@mcp.tool()
def openwebif_epg_now_next(
    service_ref: Annotated[str, Field(description="Service/channel reference.")],
) -> Any:
    """Return now/next EPG entries for one service."""
    return _ok(client.api("epgnownext", {"sRef": service_ref}))


@mcp.tool()
def openwebif_timers() -> Any:
    """List existing recording and zap timers."""
    return _ok(client.api("timerlist"))


@mcp.tool()
def openwebif_add_timer(
    service_ref: Annotated[str, Field(description="Service/channel reference.")],
    begin: Annotated[int, Field(description="Unix timestamp for recording start.")],
    end: Annotated[int, Field(description="Unix timestamp for recording end.")],
    name: Annotated[str, Field(description="Timer name/title.")],
    description: Annotated[str | None, Field(description="Optional timer description.")] = None,
    dirname: Annotated[str | None, Field(description="Optional target recording directory.")] = None,
    tags: Annotated[str | None, Field(description="Optional space-separated OpenWebif tags.")] = None,
    disabled: Annotated[bool, Field(description="Create timer disabled.")] = False,
    justplay: Annotated[bool, Field(description="Create a zap/play timer instead of a recording.")] = False,
    afterevent: Annotated[
        int,
        Field(description="1=standby, 2=deep standby, 3=auto after timer ends."),
    ] = 3,
    always_zap: Annotated[bool, Field(description="Zap to service before the timer.")] = False,
) -> Any:
    """Create a recording or zap timer with explicit start/end timestamps."""
    client.require_mutations_enabled()
    return _ok(
        client.api(
            "timeradd",
            {
                "sRef": service_ref,
                "begin": begin,
                "end": end,
                "name": name,
                "description": description,
                "dirname": dirname,
                "tags": tags,
                "disabled": int(disabled),
                "justplay": int(justplay),
                "afterevent": afterevent,
                "always_zap": int(always_zap),
            },
        )
    )


@mcp.tool()
def openwebif_add_timer_by_event_id(
    service_ref: Annotated[str, Field(description="Service/channel reference.")],
    event_id: Annotated[int, Field(description="EPG event id from OpenWebif.")],
    justplay: Annotated[bool, Field(description="Create a zap/play timer instead of a recording.")] = False,
    dirname: Annotated[str | None, Field(description="Optional target recording directory.")] = None,
    tags: Annotated[str | None, Field(description="Optional space-separated OpenWebif tags.")] = None,
    always_zap: Annotated[bool, Field(description="Zap to service before the timer.")] = False,
) -> Any:
    """Create a timer directly from an EPG event id."""
    client.require_mutations_enabled()
    return _ok(
        client.api(
            "timeraddbyeventid",
            {
                "sRef": service_ref,
                "eventid": event_id,
                "justplay": int(justplay),
                "dirname": dirname,
                "tags": tags,
                "always_zap": int(always_zap),
            },
        )
    )


@mcp.tool()
def openwebif_delete_timer(
    service_ref: Annotated[str, Field(description="Timer service reference.")],
    begin: Annotated[int, Field(description="Original timer begin timestamp.")],
    end: Annotated[int, Field(description="Original timer end timestamp.")],
) -> Any:
    """Delete an existing timer by service reference and original begin/end timestamps."""
    client.require_mutations_enabled()
    return _ok(client.api("timerdelete", {"sRef": service_ref, "begin": begin, "end": end}))


@mcp.tool()
def openwebif_toggle_timer(
    service_ref: Annotated[str, Field(description="Timer service reference.")],
    begin: Annotated[int, Field(description="Original timer begin timestamp.")],
    end: Annotated[int, Field(description="Original timer end timestamp.")],
) -> Any:
    """Enable or disable an existing timer."""
    client.require_mutations_enabled()
    return _ok(client.api("timertogglestatus", {"sRef": service_ref, "begin": begin, "end": end}))


@mcp.tool()
def openwebif_record_now(
    infinite: Annotated[bool, Field(description="Record until stopped by the user.")] = False,
) -> Any:
    """Start an immediate recording on the receiver."""
    client.require_mutations_enabled()
    return _ok(client.api("recordnow", {"infinite": int(infinite)}))


@mcp.tool()
def openwebif_zap(
    service_ref: Annotated[str, Field(description="Service/channel reference to switch to.")],
) -> Any:
    """Switch the receiver to another service/channel."""
    client.require_mutations_enabled()
    return _ok(client.api("zap", {"sRef": service_ref}))


@mcp.tool()
def openwebif_send_message(
    text: Annotated[str, Field(description="Text to display on the receiver.")],
    timeout_seconds: Annotated[int, Field(description="How long to show the message.")] = 10,
    message_type: Annotated[
        int,
        Field(description="OpenWebif message type: 0=yes/no, 1=info, 2=warning, 3=error."),
    ] = 1,
) -> Any:
    """Show a message on the TV through the receiver."""
    client.require_mutations_enabled()
    return _ok(client.api("message", {"text": text, "timeout": timeout_seconds, "type": message_type}))


@mcp.tool()
def openwebif_remote_control(
    command: Annotated[
        int,
        Field(description="OpenWebif remote-control command code, e.g. 352=OK, 103=up, 108=down."),
    ],
) -> Any:
    """Send a remote-control key code to the receiver."""
    client.require_mutations_enabled()
    return _ok(client.api("remotecontrol", {"command": command}))


@mcp.tool()
def openwebif_movies(
    dirname: Annotated[str | None, Field(description="Optional recording directory path.")] = None,
    tag: Annotated[str | None, Field(description="Optional movie tag filter.")] = None,
) -> Any:
    """List recordings/movies known to OpenWebif."""
    return _ok(client.api("movielist", {"dirname": dirname, "tag": tag}))


@mcp.tool()
def openwebif_locations() -> Any:
    """List configured recording locations."""
    return _ok(client.api("getlocations"))


def main() -> None:
    host = os.environ.get("MCP_HOST", "0.0.0.0")
    port = int(os.environ.get("MCP_PORT", "8000"))
    mcp.settings.host = host
    mcp.settings.port = port
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
