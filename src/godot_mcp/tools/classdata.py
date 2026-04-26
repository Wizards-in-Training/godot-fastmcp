"""Tools for managing Godot class reference data."""

from __future__ import annotations

from fastmcp import FastMCP

from godot_mcp.classdata.loader import (
    _DATA_DIR,
    _detect_project_version,
    _find_godot_executable,
    _godot_version_string,
    _versioned_api_path,
    generate_extension_api,
)

mcp: FastMCP = FastMCP("classdata-tools")


@mcp.tool(
    annotations={"readOnlyHint": True},
)
def classdata_status() -> dict:
    """Check the status of Godot class reference data for the current project.

    Returns the detected project Godot version, which cached data files exist,
    and whether a Godot executable can be found for generating missing data.
    """
    project_version = _detect_project_version()
    godot_exe = _find_godot_executable()
    godot_version = _godot_version_string(godot_exe) if godot_exe else None

    # List all cached version files
    cached: list[str] = []
    if _DATA_DIR.exists():
        for f in sorted(_DATA_DIR.glob("extension_api*.json")):
            cached.append(f.name)

    ready = False
    if project_version:
        ready = _versioned_api_path(project_version).exists()
    elif cached:
        # No project version detected but some data exists — usable as fallback
        ready = True

    return {
        "project_godot_version": project_version,
        "classdata_ready": ready,
        "cached_versions": cached,
        "godot_executable_found": godot_exe,
        "godot_executable_version": godot_version,
        "hint": (
            None
            if ready
            else (
                "Call classdata_generate to generate class reference data."
                if godot_exe
                else "Set GODOT_EXECUTABLE to your Godot binary path, then call classdata_generate."
            )
        ),
    }


@mcp.tool()
def classdata_generate(godot_executable: str | None = None) -> dict:
    """Generate (or regenerate) Godot class reference data.

    Runs the local Godot binary with --dump-extension-api and caches the result
    by Godot major.minor version (e.g. extension_api_4_3.json).

    Args:
        godot_executable: Path to the Godot binary. If omitted, searches common
                          install locations automatically.
    """
    exe = godot_executable or _find_godot_executable()
    if not exe:
        return {
            "success": False,
            "error": (
                "Godot executable not found. "
                "Pass the path explicitly: classdata_generate(godot_executable='/path/to/godot')"
            ),
        }

    version = _godot_version_string(exe)
    try:
        path = generate_extension_api(exe)
        return {
            "success": True,
            "godot_version": version,
            "output_file": str(path),
        }
    except RuntimeError as e:
        return {
            "success": False,
            "godot_version": version,
            "error": str(e),
        }
