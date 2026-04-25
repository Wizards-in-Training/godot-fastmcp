"""Resource (.tres) file tools for Godot MCP."""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from godot_mcp.config import get_project_root, resolve_project_path
from godot_mcp.parsers.tscn import TscnFile, parse_tres, tscn_to_dict

mcp = FastMCP("resource")


@mcp.tool(annotations={"readOnlyHint": True})
def resource_read(path: str) -> dict[str, Any]:
    """Parse a Godot resource file (.tres) and return its structure as JSON.

    Args:
        path: Path to the .tres file (res:// format or relative to project root).

    Returns the resource type, properties, and any embedded sub-resources.
    """
    root = get_project_root()
    abs_path = resolve_project_path(root, path)
    if not abs_path.exists():
        raise FileNotFoundError(f"Resource file not found: {path}")
    if abs_path.suffix != ".tres":
        raise ValueError(f"Not a .tres file: {path}")
    tscn = parse_tres(abs_path.read_text(encoding="utf-8"))
    return tscn_to_dict(tscn)


@mcp.tool()
def resource_create(
    path: str,
    resource_type: str,
    properties: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a new Godot resource file (.tres).

    Args:
        path: Where to create the .tres file (res:// format).
        resource_type: The Godot resource class (e.g. "Resource", "Theme", "SpriteFrames").
        properties: Optional dict of property name -> Godot value string to set.

    Returns the new resource structure.
    """
    root = get_project_root()
    abs_path = resolve_project_path(root, path)

    if abs_path.exists():
        raise FileExistsError(f"Resource already exists: {path}.")
    if abs_path.suffix != ".tres":
        raise ValueError(f"Path must end with .tres, got: {path}")

    from godot_mcp.parsers.values import parse_value

    parsed_props: dict[str, Any] = {}
    if properties:
        for k, v in properties.items():
            if isinstance(v, str):
                try:
                    parsed_props[k] = parse_value(v)
                except Exception:
                    parsed_props[k] = v
            else:
                parsed_props[k] = v

    tres = TscnFile(
        is_resource=True,
        resource_type=resource_type,
        header_attrs={"format": "3"},
        resource_properties=parsed_props,
    )

    abs_path.parent.mkdir(parents=True, exist_ok=True)
    abs_path.write_text(tres.to_tscn(), encoding="utf-8")
    return tscn_to_dict(tres)
