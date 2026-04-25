"""Godot 4 MCP server."""

from godot_mcp.server import create_server


def main() -> None:
    """Entry point for the godot-mcp server."""
    mcp = create_server()
    mcp.run()


__all__ = ["main", "create_server"]
