"""Run the HTTP API and the five MCP servers in one container."""

from __future__ import annotations

import os
import signal
import subprocess
import sys

COMMANDS = (
    [
        sys.executable,
        "-m",
        "uvicorn",
        "jyotish_api.main:app",
        "--host",
        "0.0.0.0",
        "--port",
        "8741",
    ],
    [sys.executable, "-m", "mcp_servers.kundli_server"],
    [sys.executable, "-m", "mcp_servers.timing_server"],
    [sys.executable, "-m", "mcp_servers.forecast_server"],
    [sys.executable, "-m", "mcp_servers.compatibility_server"],
    [sys.executable, "-m", "mcp_servers.ashtakavarga_server"],
    [sys.executable, "-m", "mcp_servers.saturn_server"],
)


def main() -> None:
    env = os.environ.copy()
    env.setdefault("MCP_HOST", "0.0.0.0")
    processes: list[subprocess.Popen[bytes]] = []

    def stop(*_args: object) -> None:
        for process in processes:
            if process.poll() is None:
                process.terminate()
        for process in processes:
            try:
                process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                process.kill()
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    for command in COMMANDS:
        processes.append(subprocess.Popen(command, env=env))
    codes = [process.wait() for process in processes]
    raise SystemExit(next((code for code in codes if code), 0))


if __name__ == "__main__":
    main()
