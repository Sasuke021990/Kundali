"""MCP server for the local panchanga. Streamable HTTP on port 8748."""

from __future__ import annotations

from typing import Any

from mcp.server.mcpserver import MCPServer

from jyotish_api.service import build_panchanga
from mcp_servers.runtime import add_health, serve

server = MCPServer(
    name="jyotish-panchanga",
    title="Jyotish Panchanga",
    instructions=(
        "Return the sunrise panchanga and the Rahu, Yamaganda, and Gulika windows "
        "for the observer's location. Sunrise is topocentric, from latitude, "
        "longitude, and elevation. Do not replace those windows with a fixed clock."
    ),
)
add_health(server, "jyotish-panchanga")


@server.tool(name="get_daily_panchanga")
def get_daily_panchanga_tool(
    date: str,
    at_time: str | None = None,
    location: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    elevation_m: float | None = None,
    timezone_name: str | None = None,
    natal_chart: dict[str, Any] | None = None,
    dob: str | None = None,
    tob: str | None = None,
    birth_location: str | None = None,
) -> dict[str, Any]:
    """Local panchanga and the three daytime inauspicious windows.

    date is YYYY-MM-DD. Pass location, or latitude and longitude, or a natal
    chart (or dob, tob, and birth_location) for the observer place.
    """
    return build_panchanga(
        date,
        at_time,
        location,
        latitude,
        longitude,
        elevation_m,
        timezone_name,
        natal_chart,
        dob,
        tob,
        birth_location,
    )


if __name__ == "__main__":
    serve(server, 8748)
