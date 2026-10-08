"""MCP server for Navamsha (D9). Streamable HTTP on port 8749."""

from __future__ import annotations

from typing import Any

from mcp.server.mcpserver import MCPServer

from jyotish_api.service import build_navamsha
from mcp_servers.runtime import add_health, serve

server = MCPServer(
    name="jyotish-navamsha",
    title="Jyotish Navamsha",
    instructions=(
        "Divide each D1 sign into nine parts of 3°20' and report the D9 sign, "
        "dignity, Vargottama, and Pushkara. Do not re-query the ephemeris. "
        "Debilitated in D9 is neecha navamsha. The same sign in D1 and D9 is "
        "Vargottama."
    ),
)
add_health(server, "jyotish-navamsha")


@server.tool(name="get_navamsha_json")
def get_navamsha_json_tool(
    natal_chart: dict[str, Any] | None = None,
    dob: str | None = None,
    tob: str | None = None,
    location: str | None = None,
) -> dict[str, Any]:
    """Navamsha, Vargottama, and Pushkara from natal longitudes.

    Pass natal_chart from get_kundli_json, or dob, tob, and location.
    """
    return build_navamsha(natal_chart, dob, tob, location)


if __name__ == "__main__":
    serve(server, 8749)
