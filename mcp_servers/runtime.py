"""Start one MCP server on streamable HTTP."""

from __future__ import annotations

import os

from mcp.server.mcpserver import MCPServer
from mcp.server.transport_security import TransportSecuritySettings
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


def serve(server: MCPServer, default_port: int) -> None:
    """Bind ``server`` on MCP_HOST and MCP_PORT, or the given default port."""
    host = os.environ.get("MCP_HOST", "0.0.0.0")
    port = int(os.environ.get("MCP_PORT", str(default_port)))
    server.run(
        transport="streamable-http",
        host=host,
        port=port,
        json_response=True,
        stateless_http=True,
        transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
    )


def add_health(server: MCPServer, name: str) -> None:
    """Public GET /health for process checks. It is outside the MCP protocol."""

    @server.custom_route("/health", methods=["GET"], include_in_schema=False)
    async def health(_request: Request) -> Response:
        return JSONResponse({"status": "ok", "server": name})
