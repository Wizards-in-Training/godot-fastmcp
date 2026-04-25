"""MCP resources for Godot class reference."""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from godot_mcp.classdata.loader import get_class_summary, get_inheritance_chain, list_classes

mcp = FastMCP("classref")


@mcp.resource("godot://class/{class_name}")
def class_info(class_name: str) -> dict[str, Any]:
    """Get Godot class reference info including properties, methods, and signals.

    Args:
        class_name: The Godot class name (e.g. "Node2D", "CharacterBody2D", "Sprite2D").

    Returns class properties, methods, signals, constants, and its inheritance chain.
    Requires extension_api.json to be generated (run: uv run generate-classdata).
    """
    summary = get_class_summary(class_name)
    if summary is None:
        available = list_classes()
        raise ValueError(
            f"Class {class_name!r} not found in Godot class reference. "
            f"Available classes: {len(available)} total. "
            "Make sure extension_api.json is generated."
        )
    summary["inheritance_chain"] = get_inheritance_chain(class_name)
    return summary


@mcp.resource("godot://classes")
def all_classes() -> list[str]:
    """List all known Godot class names from the class reference.

    Requires extension_api.json to be generated (run: uv run generate-classdata).
    """
    classes = list_classes()
    if not classes:
        raise RuntimeError(
            "No class data available. Run: uv run generate-classdata"
        )
    return classes
