"""Scene read/write tools for Godot MCP."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastmcp import FastMCP

from godot_mcp.config import get_project_root, resolve_project_path
from godot_mcp.parsers.tscn import Node, TscnFile, parse_tscn, tscn_to_dict

mcp = FastMCP("scene")


def _load_scene(path: str) -> tuple[TscnFile, Path]:
    """Load and parse a scene file, returning (tscn, absolute_path)."""
    root = get_project_root()
    abs_path = resolve_project_path(root, path)
    if not abs_path.exists():
        raise FileNotFoundError(f"Scene file not found: {path}")
    if abs_path.suffix != ".tscn":
        raise ValueError(f"Not a .tscn file: {path}")
    tscn = parse_tscn(abs_path.read_text(encoding="utf-8"))
    return tscn, abs_path


@mcp.tool(annotations={"readOnlyHint": True})
def scene_read(path: str) -> dict[str, Any]:
    """Parse a Godot scene file and return its structure as JSON.

    Args:
        path: Path to the .tscn file. Use res:// format (e.g. "res://scenes/player.tscn")
              or a path relative to the project root.

    Returns the full scene structure including nodes, external resources,
    sub-resources, and signal connections.
    """
    tscn, _ = _load_scene(path)
    return tscn_to_dict(tscn)


@mcp.tool(annotations={"readOnlyHint": True})
def scene_get_node(path: str, node_path: str) -> dict[str, Any] | None:
    """Get a specific node from a scene by its path.

    Args:
        path: Path to the .tscn file (res:// format).
        node_path: Node path within the scene. Use "." for the root node,
                   or paths like "Player", "Player/Sprite2D".

    Returns the node's properties, type, and metadata, or null if not found.
    """
    tscn, _ = _load_scene(path)
    node = tscn.get_node(node_path)
    if node is None:
        return None
    from godot_mcp.parsers.tscn import _serialize_props

    return {
        "name": node.name,
        "type": node.type,
        "parent": node.parent,
        "path": node.node_path(),
        "instance_id": node.instance_id,
        "groups": node.groups,
        "properties": _serialize_props(node.properties),
    }


@mcp.tool()
def scene_add_node(
    path: str,
    parent_path: str,
    node_name: str,
    node_type: str,
    properties: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Add a new node to an existing scene.

    Args:
        path: Path to the .tscn file (res:// format).
        parent_path: Path of the parent node. Use "." for the root node.
        node_name: Name for the new node.
        node_type: Godot node type (e.g. "Node2D", "Sprite2D", "CharacterBody2D").
        properties: Optional dict of property name -> value to set on the node.

    Returns the updated scene structure.
    """
    tscn, abs_path = _load_scene(path)

    # Validate parent exists
    if parent_path != "." and tscn.get_node(parent_path) is None:
        raise ValueError(f"Parent node not found: {parent_path!r}")

    # Check for name collision
    for n in tscn.nodes:
        if n.parent == parent_path and n.name == node_name:
            raise ValueError(
                f"A node named {node_name!r} already exists under parent {parent_path!r}"
            )

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

    new_node = Node(
        name=node_name,
        type=node_type,
        parent=parent_path,
        properties=parsed_props,
    )
    tscn.nodes.append(new_node)
    abs_path.write_text(tscn.to_tscn(), encoding="utf-8")
    return tscn_to_dict(tscn)


@mcp.tool()
def scene_update_node(
    path: str,
    node_path: str,
    properties: dict[str, Any],
) -> dict[str, Any]:
    """Update properties on an existing node in a scene.

    Args:
        path: Path to the .tscn file (res:// format).
        node_path: Path of the node to update (e.g. "." for root, "Player/Sprite2D").
        properties: Dict of property name -> new value. Values can be Godot literals
                    as strings (e.g. "Vector2(10, 20)") or raw Python values.

    Returns the updated scene structure.
    """
    tscn, abs_path = _load_scene(path)
    node = tscn.get_node(node_path)
    if node is None:
        raise ValueError(f"Node not found: {node_path!r}")

    from godot_mcp.parsers.values import parse_value

    for k, v in properties.items():
        if isinstance(v, str):
            try:
                node.properties[k] = parse_value(v)
            except Exception:
                node.properties[k] = v
        else:
            node.properties[k] = v

    abs_path.write_text(tscn.to_tscn(), encoding="utf-8")
    return tscn_to_dict(tscn)


@mcp.tool(annotations={"destructiveHint": True})
def scene_remove_node(path: str, node_path: str) -> dict[str, Any]:
    """Remove a node (and all its children) from a scene.

    Args:
        path: Path to the .tscn file (res:// format).
        node_path: Path of the node to remove. Cannot remove the root node.

    Returns the updated scene structure.
    """
    tscn, abs_path = _load_scene(path)

    if node_path == ".":
        raise ValueError("Cannot remove the root node.")

    node = tscn.get_node(node_path)
    if node is None:
        raise ValueError(f"Node not found: {node_path!r}")

    # Remove node and all descendants
    def is_descendant(candidate: Node, ancestor_path: str) -> bool:
        p = candidate.parent or ""
        while p:
            if p == ancestor_path:
                return True
            # Walk up
            if "/" in p:
                p = p.rsplit("/", 1)[0]
            else:
                break
        return False

    target_path = node.node_path()
    tscn.nodes = [
        n for n in tscn.nodes if n.node_path() != target_path and not is_descendant(n, target_path)
    ]

    # Also remove connections involving this node
    tscn.connections = [
        c for c in tscn.connections if c.from_node != target_path and c.to_node != target_path
    ]

    abs_path.write_text(tscn.to_tscn(), encoding="utf-8")
    return tscn_to_dict(tscn)


@mcp.tool()
def scene_create(
    path: str,
    root_name: str,
    root_type: str = "Node",
) -> dict[str, Any]:
    """Create a new Godot scene file with a single root node.

    Args:
        path: Where to create the .tscn file (res:// format, e.g. "res://scenes/player.tscn").
        root_name: Name for the root node (e.g. "Player").
        root_type: Godot node type for the root (default: "Node"). Common values:
                   "Node2D", "Node3D", "Control", "CharacterBody2D", "Area2D".

    Returns the new scene structure.
    """
    root = get_project_root()
    abs_path = resolve_project_path(root, path)

    if abs_path.exists():
        raise FileExistsError(f"Scene already exists: {path}. Use scene_add_node to modify it.")
    if abs_path.suffix != ".tscn":
        raise ValueError(f"Path must end with .tscn, got: {path}")

    abs_path.parent.mkdir(parents=True, exist_ok=True)

    tscn = TscnFile(header_attrs={"format": "3", "uid": ""})
    root_node = Node(name=root_name, type=root_type, parent=None)
    tscn.nodes.append(root_node)

    abs_path.write_text(tscn.to_tscn(), encoding="utf-8")
    return tscn_to_dict(tscn)
