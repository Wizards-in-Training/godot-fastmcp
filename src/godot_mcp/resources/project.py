"""MCP resources for Godot project information."""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from godot_mcp.config import get_project_root, resolve_project_path
from godot_mcp.parsers.project_config import get_autoloads, parse_project_config
from godot_mcp.parsers.tscn import parse_tscn, tscn_to_dict

mcp = FastMCP("project-resources")


@mcp.resource("godot://project/settings")
def project_settings() -> dict[str, Any]:
    """Full parsed project.godot as a structured JSON object.

    Contains all project settings grouped by section (application, rendering,
    physics, input, autoload, etc.).
    """
    root = get_project_root()
    config = parse_project_config(root / "project.godot")
    # Convert any non-JSON-safe values to strings
    return _make_serializable(config)


@mcp.resource("godot://project/autoloads")
def project_autoloads() -> dict[str, str]:
    """List of autoload singletons as {name: res_path} pairs."""
    root = get_project_root()
    config = parse_project_config(root / "project.godot")
    return get_autoloads(config)


@mcp.resource("godot://scene/{path}")
def scene_resource(path: str) -> dict[str, Any]:
    """Parsed scene file at the given res:// path.

    Args:
        path: The scene path after 'godot://scene/' — e.g. 'scenes/player.tscn'
              which maps to 'res://scenes/player.tscn'.
    """
    root = get_project_root()
    res_path = f"res://{path}"
    abs_path = resolve_project_path(root, res_path)
    if not abs_path.exists():
        raise FileNotFoundError(f"Scene not found: {res_path}")
    tscn = parse_tscn(abs_path.read_text(encoding="utf-8"))
    return tscn_to_dict(tscn)


def _make_serializable(obj: Any) -> Any:
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj
    if isinstance(obj, list):
        return [_make_serializable(i) for i in obj]
    if isinstance(obj, dict):
        return {str(k): _make_serializable(v) for k, v in obj.items()}
    return str(obj)
