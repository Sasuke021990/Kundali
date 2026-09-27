"""MCP server for the forecast window. Streamable HTTP on port 8744."""

from __future__ import annotations

from typing import Any

from mcp.server.mcpserver import MCPServer

from jyotish_api.service import build_forecast
from mcp_servers.runtime import add_health, serve

server = MCPServer(
    name="jyotish-forecast",
    title="Jyotish Forecast",
    instructions=(
        "Build a multi-day timeline. For a month outlook, use critical_windows and "
        "major_transits and do not walk every timeline row. For one day, use that "
        "single timeline record and call get_timing_telemetry for the degrees. "
        "Highlight dates where dasha_transition is true. Read risk_flags and "
        "tara_bala directly."
    ),
)
add_health(server, "jyotish-forecast")


@server.tool(name="generate_forecast_window")
def generate_forecast_window_tool(
    start_date: str,
    days: int = 30,
    time: str = "09:00",
    natal_chart: dict[str, Any] | None = None,
    dob: str | None = None,
    tob: str | None = None,
    location: str | None = None,
) -> dict[str, Any]:
    """Daily dasha, Tara, Chandrashtama, and combustion flags across a date window.

    start_date is YYYY-MM-DD. days defaults to 30. time is the local clock time
    used for every date and defaults to 09:00. Pass natal_chart, or dob, tob,
    and location. The timeline is concise. It is not a full ephemeris dump.
    """
    return build_forecast(start_date, days, time, natal_chart, dob, tob, location)


if __name__ == "__main__":
    serve(server, 8744)
