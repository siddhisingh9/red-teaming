"""Day 6: MCP stdio client exposing the same tool_registry dict interface
as tools/sim.py's TOOL_REGISTRY -- agent/loop.py calls
`tool_fn(**arguments, injection=..., position=...)` either way and cannot
tell which transport is behind it.

Each call spawns tools/mcp_server.py as a subprocess, opens a stdio
ClientSession, calls the tool, and tears the session down. That's a real
per-call cost (config.TRANSPORT's whole reason to default to "direct" for
day-to-day debugging), but it's far simpler and more robust than keeping a
session alive across threads, and it's exactly the overhead this day exists
to measure -- see runner.py --transport mcp vs. direct.
"""

from __future__ import annotations

import asyncio
import sys
from typing import Any, Callable

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from schemas import Position, ToolResponse
from tools.sim import _injection_id

_SERVER_PARAMS = StdioServerParameters(command=sys.executable, args=["-m", "tools.mcp_server"])


async def _list_tool_names() -> list[str]:
    async with stdio_client(_SERVER_PARAMS) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.list_tools()
            return [tool.name for tool in result.tools]


def list_tools() -> list[str]:
    """Every tool name the server advertises -- used to sanity-check it
    exposes exactly the three tools agent/prompts.py's schemas describe."""
    return asyncio.run(_list_tool_names())


async def _call_tool(name: str, arguments: dict[str, Any]) -> str:
    # Raise only after both `async with` blocks have cleanly exited, not
    # inside them: anyio's task-group-based context managers wrap any
    # exception raised mid-block into an ExceptionGroup on the way out
    # (even on Python 3.10, without native `except*`), which would turn a
    # clean "tool X errored" into an opaque "unhandled errors in a
    # TaskGroup" for every caller -- including agent/loop.py's
    # AgentRunError, whose whole point is a legible cause.
    async with stdio_client(_SERVER_PARAMS) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(name, arguments)

    text = "".join(part.text for part in result.content if part.type == "text")
    if result.is_error:
        raise RuntimeError(f"MCP tool {name!r} returned an error: {text}")
    return text


def call_tool(name: str, arguments: dict[str, Any]) -> str:
    return asyncio.run(_call_tool(name, arguments))


def _make_tool(name: str) -> Callable[..., ToolResponse]:
    def call(
        *, injection: str | None = None, position: Position = "middle", **kwargs: Any
    ) -> ToolResponse:
        arguments = {**kwargs, "injection": injection, "position": position}
        content = call_tool(name, arguments)
        return ToolResponse(
            tool_name=name,
            content=content,
            was_poisoned=injection is not None,
            injection_id=_injection_id(injection),
            position=position,
        )

    call.__name__ = name
    return call


TOOL_REGISTRY: dict[str, Callable[..., ToolResponse]] = {
    name: _make_tool(name) for name in ("web_search", "read_file", "fetch_url")
}


if __name__ == "__main__":
    print("Tools advertised over MCP:", list_tools())
