"""Project inspection tools for Godot MCP."""

from __future__ import annotations

import fnmatch
from pathlib import Path
from typing import Any

from fastmcp import FastMCP

from godot_mcp.config import get_project_root, to_res_path
from godot_mcp.parsers.project_config import (
    get_autoloads,
    get_main_scene,
    get_project_name,
    parse_project_config,
)

mcp = FastMCP("project")


def _load_gdignore(project_root: Path) -> list[str]:
    gdignore = project_root / ".gdignore"
    if gdignore.exists():
        lines = gdignore.read_text(encoding="utf-8").splitlines()
        return [ln.strip() for ln in lines if ln.strip() and not ln.startswith("#")]
    return []


def _is_ignored(path: Path, project_root: Path, patterns: list[str]) -> bool:
    rel = path.relative_to(project_root).as_posix()
    for pattern in patterns:
        if fnmatch.fnmatch(rel, pattern) or fnmatch.fnmatch(path.name, pattern):
            return True
    return False


@mcp.tool(annotations={"readOnlyHint": True})
def project_info() -> dict[str, Any]:
    """Get information about the Godot project (name, main scene, autoloads, features).

    Reads project.godot and returns a structured summary. Requires GODOT_PROJECT_PATH.
    """
    root = get_project_root()
    config = parse_project_config(root / "project.godot")

    name = get_project_name(config)
    main_scene = get_main_scene(config)
    autoloads = get_autoloads(config)

    features = config.get("application", {}).get("config/features", [])
    if not isinstance(features, list):
        features = [str(features)]

    return {
        "name": name,
        "main_scene": main_scene,
        "autoloads": autoloads,
        "features": features,
        "project_root": str(root),
        "config_version": config.get("", {}).get("config_version", "unknown"),
    }


@mcp.tool(annotations={"readOnlyHint": True})
def project_list_scenes() -> list[str]:
    """List all .tscn scene files in the Godot project as res:// paths."""
    root = get_project_root()
    ignore_patterns = _load_gdignore(root)
    scenes = []
    for p in sorted(root.rglob("*.tscn")):
        if not _is_ignored(p, root, ignore_patterns):
            scenes.append(to_res_path(root, p))
    return scenes


@mcp.tool(annotations={"readOnlyHint": True})
def project_list_scripts() -> list[str]:
    """List all GDScript (.gd) files in the Godot project as res:// paths."""
    root = get_project_root()
    ignore_patterns = _load_gdignore(root)
    scripts = []
    for p in sorted(root.rglob("*.gd")):
        if not _is_ignored(p, root, ignore_patterns):
            scripts.append(to_res_path(root, p))
    return scripts


@mcp.tool(annotations={"readOnlyHint": True})
def project_list_resources() -> list[str]:
    """List all .tres resource files in the Godot project as res:// paths."""
    root = get_project_root()
    ignore_patterns = _load_gdignore(root)
    resources = []
    for p in sorted(root.rglob("*.tres")):
        if not _is_ignored(p, root, ignore_patterns):
            resources.append(to_res_path(root, p))
    return resources


@mcp.tool(annotations={"readOnlyHint": True})
def project_file_tree(
    path: str = "res://",
    max_depth: int = 4,
) -> dict[str, Any]:
    """Get the directory tree of the Godot project.

    Args:
        path: Starting path (default: project root). Use res:// format.
        max_depth: Maximum directory depth to recurse (default: 4).

    Returns a nested dict where directory entries end with '/' and file entries
    contain size and res_path.
    """
    root = get_project_root()
    ignore_patterns = _load_gdignore(root)

    if path in ("res://", "res:"):
        start = root
    else:
        rel = path.removeprefix("res://")
        start = root / rel

    if not start.exists():
        raise ValueError(f"Path does not exist: {path}")

    def build_tree(directory: Path, depth: int) -> dict[str, Any]:
        if depth == 0:
            return {"_truncated": True}
        result: dict[str, Any] = {}
        try:
            entries = sorted(directory.iterdir(), key=lambda p: (p.is_file(), p.name))
        except PermissionError:
            return {}
        for entry in entries:
            if entry.name.startswith("."):
                continue
            if _is_ignored(entry, root, ignore_patterns):
                continue
            if entry.is_dir():
                result[entry.name + "/"] = build_tree(entry, depth - 1)
            else:
                result[entry.name] = {
                    "size": entry.stat().st_size,
                    "res_path": to_res_path(root, entry),
                }
        return result

    return build_tree(start, max_depth)
