"""MCP server for Ashtakavarga bindus. Streamable HTTP on port 8746."""

from __future__ import annotations

from typing import Any

from mcp.server.mcpserver import MCPServer

from jyotish_api.service import build_ashtakavarga
from mcp_servers.runtime import add_health, serve

server = MCPServer(
    name="jyotish-ashtakavarga",
    title="Jyotish Ashtakavarga",
    instructions=(
        "Compute Bhinnashtakavarga (0-8 per sign per graha) and Sarvashtakavarga "
        "(0-56 per sign, mean 28). Judge transits by bindus, not house alone. "
        "SAV of 32 or more protects the sign. SAV of 24 or less is weak even "
        "if the house from lagna or Moon looks good."
    ),
)
add_health(server, "jyotish-ashtakavarga")


@server.tool(name="get_ashtakavarga_json")
def get_ashtakavarga_json_tool(
    natal_chart: dict[str, Any] | None = None,
    dob: str | None = None,
    tob: str | None = None,
    location: str | None = None,
    target_date: str | None = None,
    target_time: str = "12:00",
) -> dict[str, Any]:
    """Natal Ashtakavarga tables and optional transit potency.

    Pass natal_chart from get_kundli_json, or dob, tob, and location.
    If target_date is YYYY-MM-DD, include transit_filter_status for Jupiter,
    Saturn, Rahu, and Ketu using the natal SAV of the occupied signs.
    """
    return build_ashtakavarga(
        natal_chart, dob, tob, location, target_date, target_time
    )


if __name__ == "__main__":
    serve(server, 8746)
