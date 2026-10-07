"""MCP server for Saturn's multi-year cycles. Streamable HTTP on port 8747."""

from __future__ import annotations

from typing import Any

from mcp.server.mcpserver import MCPServer

from jyotish_api.service import build_saturn_cycles
from mcp_servers.runtime import add_health, serve

server = MCPServer(
    name="jyotish-saturn",
    title="Jyotish Saturn Cycles",
    instructions=(
        "Track Sade Sati, Kantaka Shani, and Ashtama Shani from sidereal Saturn "
        "ingresses. Sade Sati is the 12th, 1st, and 2nd from the natal Moon. "
        "Kantaka is the 4th from the Moon or the lagna. Ashtama is the 8th from "
        "the Moon. Report the dates returned by the tool without changing them."
    ),
)
add_health(server, "jyotish-saturn")


@server.tool(name="get_saturn_cycles")
def get_saturn_cycles_tool(
    as_of_date: str,
    as_of_time: str = "09:00",
    natal_chart: dict[str, Any] | None = None,
    dob: str | None = None,
    tob: str | None = None,
    location: str | None = None,
) -> dict[str, Any]:
    """Multi-year Saturn cycles at one local civil moment.

    as_of_date is YYYY-MM-DD. as_of_time defaults to 09:00 in the natal timezone.
    Pass natal_chart, or dob, tob, and location.
    """
    return build_saturn_cycles(
        as_of_date, as_of_time, natal_chart, dob, tob, location
    )


if __name__ == "__main__":
    serve(server, 8747)
