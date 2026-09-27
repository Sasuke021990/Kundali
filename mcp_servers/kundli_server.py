"""MCP server for the natal Kundli tool. Streamable HTTP on port 8742."""

from __future__ import annotations

from typing import Any

from mcp.server.mcpserver import MCPServer

from jyotish_api.service import build_kundli
from mcp_servers.runtime import add_health, serve

server = MCPServer(
    name="jyotish-kundli",
    title="Jyotish Kundli",
    instructions=(
        "Calculate a Lahiri sidereal natal chart. Pass the returned object as "
        "natal_chart to the timing and forecast servers. Rahu is the mean node. "
        "Read is_combust, is_in_graha_yuddha, and aspected_houses from each graha "
        "instead of inferring them."
    ),
)
add_health(server, "jyotish-kundli")


@server.tool(name="get_kundli_json")
def get_kundli_json_tool(dob: str, tob: str, location: str) -> dict[str, Any]:
    """Natal Kundli for a birth date, time, and place.

    dob is YYYY-MM-DD. tob is 24-hour HH:MM in the local civil time of location.
    location is a place name such as "Hubli, Karnataka". The result includes
    metadata, lagna, nine grahas, and twelve whole-sign houses.
    """
    return build_kundli(dob, tob, location)


if __name__ == "__main__":
    serve(server, 8742)
