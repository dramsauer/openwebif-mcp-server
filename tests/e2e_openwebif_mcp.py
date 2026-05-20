from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin

import httpx


DEFAULT_PROTOCOL_VERSION = "2025-11-25"


class TestFailure(AssertionError):
    pass


@dataclass
class TestResult:
    name: str
    elapsed: float


class Runner:
    def __init__(self) -> None:
        self.results: list[TestResult] = []

    def run(self, name: str, fn) -> None:
        start = time.perf_counter()
        print(f"==> {name}", flush=True)
        fn()
        elapsed = time.perf_counter() - start
        self.results.append(TestResult(name=name, elapsed=elapsed))
        print(f"ok  {name} ({elapsed:.2f}s)", flush=True)

    def summary(self) -> None:
        print("\nSummary:", flush=True)
        for result in self.results:
            print(f"- {result.name}: {result.elapsed:.2f}s", flush=True)


def require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise TestFailure(f"{name} is required")
    return value


def assert_mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TestFailure(f"{label} should be an object, got {type(value).__name__}")
    if value.get("result") is False:
        raise TestFailure(f"{label} returned result=false: {value}")
    return value


def openwebif_get(client: httpx.Client, base_url: str, method: str, params: dict[str, Any] | None = None):
    response = client.get(urljoin(base_url.rstrip("/") + "/", f"api/{method}"), params=params)
    response.raise_for_status()
    return response.json()


class McpJsonRpcClient:
    def __init__(self, url: str):
        self.url = url
        self.next_id = 1
        self.client = httpx.Client(
            timeout=20,
            headers={
                "Accept": "application/json, text/event-stream",
                "Content-Type": "application/json",
            },
        )

    def request(self, method: str, params: dict[str, Any] | None = None) -> Any:
        request_id = self.next_id
        self.next_id += 1
        payload: dict[str, Any] = {"jsonrpc": "2.0", "id": request_id, "method": method}
        if params is not None:
            payload["params"] = params

        response = self.client.post(self.url, json=payload)
        response.raise_for_status()
        data = self._decode_response(response)

        if data.get("id") != request_id:
            raise TestFailure(f"Unexpected JSON-RPC id for {method}: {data}")
        if "error" in data:
            raise TestFailure(f"MCP request {method} failed: {data['error']}")
        return data.get("result")

    def notify(self, method: str, params: dict[str, Any] | None = None) -> None:
        payload: dict[str, Any] = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            payload["params"] = params
        response = self.client.post(self.url, json=payload)
        response.raise_for_status()

    def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> Any:
        result = self.request("tools/call", {"name": name, "arguments": arguments or {}})
        if not isinstance(result, dict):
            raise TestFailure(f"Tool {name} returned an unexpected MCP result: {result}")
        if result.get("isError"):
            raise TestFailure(f"Tool {name} returned isError=true: {result}")

        content = result.get("content", [])
        if not content:
            return result
        first = content[0]
        if isinstance(first, dict) and first.get("type") == "text":
            text = first.get("text", "")
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return text
        return content

    @staticmethod
    def _decode_response(response: httpx.Response) -> dict[str, Any]:
        content_type = response.headers.get("content-type", "")
        if "text/event-stream" in content_type:
            for line in response.text.splitlines():
                if line.startswith("data: "):
                    return json.loads(line.removeprefix("data: "))
            raise TestFailure(f"No data line found in SSE response: {response.text}")
        data = response.json()
        if not isinstance(data, dict):
            raise TestFailure(f"JSON-RPC response should be an object: {data}")
        return data


def wait_for_mcp(url: str, timeout_seconds: float) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            client = McpJsonRpcClient(url)
            client.request(
                "initialize",
                {
                    "protocolVersion": DEFAULT_PROTOCOL_VERSION,
                    "capabilities": {},
                    "clientInfo": {"name": "openwebif-mcp-e2e", "version": "0.1.0"},
                },
            )
            return
        except Exception as exc:  # noqa: BLE001 - keep retry diagnostics compact.
            last_error = exc
            time.sleep(0.5)
    raise TestFailure(f"MCP server did not become ready: {last_error}")


def direct_openwebif_tests() -> None:
    base_url = require_env("OPENWEBIF_BASE_URL")
    with httpx.Client(timeout=float(os.environ.get("OPENWEBIF_TIMEOUT", "10"))) as client:
        about = assert_mapping(openwebif_get(client, base_url, "about"), "about")
        status = assert_mapping(openwebif_get(client, base_url, "statusinfo"), "statusinfo")
        timers = assert_mapping(openwebif_get(client, base_url, "timerlist"), "timerlist")

    print(f"    OpenWebif about keys: {', '.join(sorted(about.keys())[:8])}", flush=True)
    print(f"    OpenWebif status keys: {', '.join(sorted(status.keys())[:8])}", flush=True)
    print(f"    OpenWebif timerlist keys: {', '.join(sorted(timers.keys())[:8])}", flush=True)


def readonly_mcp_tests(url: str) -> None:
    client = McpJsonRpcClient(url)
    initialize = client.request(
        "initialize",
        {
            "protocolVersion": DEFAULT_PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": "openwebif-mcp-e2e", "version": "0.1.0"},
        },
    )
    assert_mapping(initialize, "initialize")
    client.notify("notifications/initialized")

    tools_result = client.request("tools/list")
    tools = tools_result.get("tools", []) if isinstance(tools_result, dict) else []
    tool_names = {tool.get("name") for tool in tools if isinstance(tool, dict)}
    expected_tools = {
        "openwebif_about",
        "openwebif_status",
        "openwebif_timers",
        "openwebif_bouquets",
        "openwebif_epg_search",
        "openwebif_add_timer",
    }
    missing = sorted(expected_tools - tool_names)
    if missing:
        raise TestFailure(f"MCP tools/list is missing expected tools: {missing}")

    assert_mapping(client.call_tool("openwebif_about"), "tool openwebif_about")
    assert_mapping(client.call_tool("openwebif_status"), "tool openwebif_status")
    assert_mapping(client.call_tool("openwebif_timers"), "tool openwebif_timers")

    print(f"    MCP exposed {len(tool_names)} tools", flush=True)


def mutation_guard_test(url: str) -> None:
    if os.environ.get("OPENWEBIF_ALLOW_MUTATIONS", "").lower() in {"1", "true", "yes", "on"}:
        print("    skipped: OPENWEBIF_ALLOW_MUTATIONS is enabled", flush=True)
        return

    client = McpJsonRpcClient(url)
    client.request(
        "initialize",
        {
            "protocolVersion": DEFAULT_PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": "openwebif-mcp-e2e", "version": "0.1.0"},
        },
    )
    client.notify("notifications/initialized")

    result = client.request(
        "tools/call",
        {"name": "openwebif_send_message", "arguments": {"text": "mutation guard test"}},
    )
    if not isinstance(result, dict) or not result.get("isError"):
        raise TestFailure(f"Expected mutation tool to be blocked, got: {result}")


def mutation_smoke_test(url: str) -> None:
    allow_smoke = os.environ.get("E2E_ALLOW_MUTATION_SMOKE", "").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    allow_mutations = os.environ.get("OPENWEBIF_ALLOW_MUTATIONS", "").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    if not allow_smoke:
        print("    skipped: set E2E_ALLOW_MUTATION_SMOKE=true to show a receiver message", flush=True)
        return
    if not allow_mutations:
        raise TestFailure("E2E_ALLOW_MUTATION_SMOKE requires OPENWEBIF_ALLOW_MUTATIONS=true")

    client = McpJsonRpcClient(url)
    client.request(
        "initialize",
        {
            "protocolVersion": DEFAULT_PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": "openwebif-mcp-e2e", "version": "0.1.0"},
        },
    )
    client.notify("notifications/initialized")
    assert_mapping(
        client.call_tool(
            "openwebif_send_message",
            {
                "text": "OpenWebif MCP E2E smoke test",
                "timeout_seconds": 5,
                "message_type": 1,
            },
        ),
        "tool openwebif_send_message",
    )


def start_mcp_process(port: int) -> subprocess.Popen[str]:
    env = os.environ.copy()
    env["MCP_HOST"] = "127.0.0.1"
    env["MCP_PORT"] = str(port)
    return subprocess.Popen(
        ["openwebif-mcp"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run OpenWebif MCP end-to-end tests.")
    parser.add_argument("--skip-direct", action="store_true", help="Skip direct OpenWebif HTTP tests.")
    parser.add_argument("--skip-mcp", action="store_true", help="Skip MCP HTTP tests.")
    parser.add_argument(
        "--mcp-url",
        default=os.environ.get("E2E_MCP_URL"),
        help="Use an already running MCP server instead of starting one.",
    )
    parser.add_argument("--port", type=int, default=int(os.environ.get("E2E_MCP_PORT", "8765")))
    args = parser.parse_args()

    runner = Runner()
    process: subprocess.Popen[str] | None = None

    try:
        if not args.skip_direct:
            runner.run("direct OpenWebif API", direct_openwebif_tests)

        if not args.skip_mcp:
            mcp_url = args.mcp_url or f"http://127.0.0.1:{args.port}/mcp"
            if args.mcp_url is None:
                process = start_mcp_process(args.port)
                wait_for_mcp(mcp_url, timeout_seconds=20)

            runner.run("MCP tools/list and read-only calls", lambda: readonly_mcp_tests(mcp_url))
            runner.run("MCP mutation guard", lambda: mutation_guard_test(mcp_url))
            runner.run("MCP optional mutation smoke", lambda: mutation_smoke_test(mcp_url))

        runner.summary()
        return 0
    except Exception as exc:  # noqa: BLE001 - CLI test runner should report any failure.
        print(f"\nFAILED: {exc}", file=sys.stderr, flush=True)
        if process and process.stdout:
            print("\nMCP server output:", file=sys.stderr, flush=True)
            print(process.stdout.read(), file=sys.stderr, flush=True)
        return 1
    finally:
        if process:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()


if __name__ == "__main__":
    raise SystemExit(main())
