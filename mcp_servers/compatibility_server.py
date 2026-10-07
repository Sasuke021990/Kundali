"""MCP server for Ashtakoota compatibility. Streamable HTTP on port 8745."""

from __future__ import annotations

from typing import Any

from mcp.server.mcpserver import MCPServer

from jyotish_api.service import build_compatibility
from mcp_servers.runtime import add_health, serve

server = MCPServer(
    name="jyotish-compatibility",
    title="Jyotish Compatibility",
    instructions=(
        "Match a groom chart and a bride chart with 36-guna Ashtakoota, Manglik "
        "dosha from both lagna and Moon, and 7th-house synastry. Do not swap "
        "male_chart and female_chart: Varna and Gana are not symmetric. A high "
        "guna score does not cancel an active Nadi dosha or a one-sided Manglik dosha."
    ),
)
add_health(server, "jyotish-compatibility")


@server.tool(name="get_compatibility_json")
def get_compatibility_json_tool(
    male_chart: dict[str, Any] | None = None,
    female_chart: dict[str, Any] | None = None,
    male_dob: str | None = None,
    male_tob: str | None = None,
    male_location: str | None = None,
    female_dob: str | None = None,
    female_tob: str | None = None,
    female_location: str | None = None,
) -> dict[str, Any]:
    """36-guna Milan, Manglik analysis, and 7th-house synastry.

    Pass male_chart and female_chart from get_kundli_json, or birth fields for
    each person. male_dob and female_dob are YYYY-MM-DD. Times are HH:MM.
    Keep the groom on the male arguments and the bride on the female arguments.
    """
    return build_compatibility(
        male_chart,
        female_chart,
        male_dob,
        male_tob,
        male_location,
        female_dob,
        female_tob,
        female_location,
    )


if __name__ == "__main__":
    serve(server, 8745)
