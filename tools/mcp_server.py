"""Day 6: MCP stdio server exposing the same three tools as tools/sim.py,
over the real protocol.

This is the point of the whole day: an in-process function call and a tool
response arriving over MCP are not the same thing to test against. Running
the tools behind stdio is what makes "tool output is untrusted input"
literally true rather than an in-process convention the agent loop could
just as easily bypass.

Reference note: requirements.txt pins mcp==2.1.1, where FastMCP was renamed
to MCPServer (mcp.server.mcpserver.MCPServer) -- `from mcp.server.fastmcp
import FastMCP` (mcp 1.x) raises ModuleNotFoundError on this version. The
decorator/run API is otherwise unchanged: @mcp.tool() and
mcp.run(transport="stdio").
"""

from __future__ import annotations

from mcp.server.mcpserver import MCPServer

from schemas import Position
from tools.sim import fetch_url as _fetch_url
from tools.sim import read_file as _read_file
from tools.sim import web_search as _web_search

mcp = MCPServer("poisoned-tools")


@mcp.tool()
def web_search(query: str, injection: str | None = None, position: Position = "middle") -> str:
    """Search the web and return the top results."""
    return _web_search(query, injection, position).content


@mcp.tool()
def read_file(path: str, injection: str | None = None, position: Position = "middle") -> str:
    """Read the text contents of a file given its path."""
    return _read_file(path, injection, position).content


@mcp.tool()
def fetch_url(url: str, injection: str | None = None, position: Position = "middle") -> str:
    """Fetch the text content of a single web page given its URL."""
    return _fetch_url(url, injection, position).content


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
