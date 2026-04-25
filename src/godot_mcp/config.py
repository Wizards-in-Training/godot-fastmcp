"""Configuration and path security for godot-mcp."""

from __future__ import annotations

import os
from pathlib import Path


def get_project_root() -> Path:
    """Return the validated Godot project root from GODOT_PROJECT_PATH env var."""
    raw = os.environ.get("GODOT_PROJECT_PATH", "")
    if not raw:
        raise OSError(
            "GODOT_PROJECT_PATH environment variable is not set. "
            "Point it at the directory containing your project.godot file."
        )
    root = Path(raw).expanduser().resolve()
    if not root.is_dir():
        raise OSError(f"GODOT_PROJECT_PATH does not exist or is not a directory: {root}")
    if not (root / "project.godot").exists():
        raise OSError(
            f"No project.godot found in GODOT_PROJECT_PATH: {root}\n"
            "Make sure this points to the root of a Godot 4 project."
        )
    return root


def get_godot_executable() -> str:
    """Return the Godot executable path from GODOT_EXECUTABLE env var (default: 'godot')."""
    return os.environ.get("GODOT_EXECUTABLE", "godot")


def resolve_project_path(project_root: Path, path: str) -> Path:
    """Resolve a path relative to the project root, rejecting path traversal.

    Accepts either:
    - A res:// path (e.g. "res://scenes/player.tscn")
    - A relative path (e.g. "scenes/player.tscn")
    - An absolute path that must be inside the project root

    Raises ValueError if the resolved path escapes the project root.
    """
    if path.startswith("res://"):
        rel = path[len("res://") :]
        resolved = (project_root / rel).resolve()
    else:
        resolved = Path(path).expanduser()
        if not resolved.is_absolute():
            resolved = (project_root / resolved).resolve()
        else:
            resolved = resolved.resolve()

    # Security: reject traversal outside project root
    try:
        resolved.relative_to(project_root)
    except ValueError:
        raise ValueError(
            f"Path '{path}' resolves outside the project root '{project_root}'. "
            "Path traversal is not allowed."
        )
    return resolved


def to_res_path(project_root: Path, absolute_path: Path) -> str:
    """Convert an absolute path inside the project to a res:// path."""
    rel = absolute_path.relative_to(project_root)
    return f"res://{rel.as_posix()}"
