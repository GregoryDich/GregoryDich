"""``python -m mcp_server`` serves stdio; ``--transport http`` serves streamable HTTP."""

from __future__ import annotations

import argparse

from .server import mcp


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="tonamorph-growth", description="Tonamorph growth MCP server"
    )
    parser.add_argument("--transport", choices=("stdio", "http"), default="stdio")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--path", default="/mcp", help="HTTP endpoint path")
    args = parser.parse_args(argv)
    if args.transport == "stdio":
        mcp.run(transport="stdio", show_banner=False)
    else:
        mcp.run(transport="http", host=args.host, port=args.port, path=args.path, show_banner=False)


if __name__ == "__main__":
    main()
