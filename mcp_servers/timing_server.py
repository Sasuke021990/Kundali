"""MCP server for dasha and transit telemetry. Streamable HTTP on port 8743."""

from __future__ import annotations

from typing import Any

from mcp.server.mcpserver import MCPServer

from jyotish_api.service import build_timing
from mcp_servers.runtime import add_health, serve

server = MCPServer(
    name="jyotish-timing",
    title="Jyotish Timing",
    instructions=(
        "Compute the active Vimshottari period and Lahiri transits for one civil "
        "moment. If is_chandrashtama is true, emphasize caution for emotional "
        "decisions, contracts, and high-risk commitments. If Mercury is combust, "
        "treat intellectual and partnership decisions with caution even when the "
        "dasha lords look supportive."
    ),
)
add_health(server, "jyotish-timing")


@server.tool(name="get_timing_telemetry")
def get_timing_telemetry_tool(
    target_date: str,
    target_time: str = "12:00",
    natal_chart: dict[str, Any] | None = None,
    dob: str | None = None,
    tob: str | None = None,
    location: str | None = None,
) -> dict[str, Any]:
    """Dasha tree, gochara, Tara Bala, and Chandrashtama for one local date.

    Pass natal_chart from get_kundli_json, or dob, tob, and location. target_date
    is YYYY-MM-DD. target_time is HH:MM in the natal timezone and defaults to noon.
    Combine this object with the natal chart. Do not recompute dasha with a flat
    365-day year.
    """
    return build_timing(target_date, target_time, natal_chart, dob, tob, location)


if __name__ == "__main__":
    serve(server, 8743)
