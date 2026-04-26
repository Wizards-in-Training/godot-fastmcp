"""Loads and indexes Godot's extension_api.json for class reference lookups.

Classdata is cached per Godot major.minor version (e.g. extension_api_4_3.json).
On first lookup the loader:
  1. Reads the target version from the current project's project.godot.
  2. Checks if a cached file for that version already exists.
  3. If not, auto-discovers the Godot executable and generates it.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

_DATA_DIR = Path(__file__).parent / "data"

# In-process cache: version string (e.g. "4.3") → class index dict
_index_cache: dict[str, dict[str, Any]] = {}


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------


def _versioned_api_path(version: str) -> Path:
    """Return the cache path for a given major.minor version string."""
    safe = version.replace(".", "_")
    return _DATA_DIR / f"extension_api_{safe}.json"


def _legacy_api_path() -> Path:
    """Unversioned fallback used by old installations."""
    return _DATA_DIR / "extension_api.json"


def get_api_path(version: str | None = None) -> Path:
    """Return the data path for the given version (or the legacy path)."""
    return _versioned_api_path(version) if version else _legacy_api_path()


# ---------------------------------------------------------------------------
# Godot executable discovery
# ---------------------------------------------------------------------------

_GODOT_SEARCH_PATHS = [
    # macOS app bundles
    "/Applications/Godot.app/Contents/MacOS/Godot",
    "/Applications/Godot_v4.app/Contents/MacOS/Godot",
    "~/Applications/Godot.app/Contents/MacOS/Godot",
    "~/Applications/Godot_v4.app/Contents/MacOS/Godot",
    # Linux common locations
    "/usr/local/bin/godot4",
    "/usr/bin/godot4",
    "/usr/local/bin/godot",
    "/usr/bin/godot",
    # Flatpak
    "~/.local/share/flatpak/exports/bin/org.godotengine.Godot",
    # Homebrew (macOS arm/intel)
    "/opt/homebrew/bin/godot",
]


def _find_godot_executable() -> str | None:
    """Search PATH and common install locations for the Godot executable."""
    import shutil

    for name in ("godot", "godot4"):
        if shutil.which(name):
            return name

    for raw in _GODOT_SEARCH_PATHS:
        path = Path(raw).expanduser()
        if path.exists():
            return str(path)

    return None


def _godot_version_string(godot_executable: str) -> str | None:
    """Return 'major.minor' from `godot --version` output (e.g. '4.3')."""
    try:
        result = subprocess.run(
            [godot_executable, "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        # Output looks like: "4.3.stable.official.77dcf073d"
        m = re.match(r"(\d+\.\d+)", result.stdout.strip())
        if m:
            return m.group(1)
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------


def generate_extension_api(
    godot_executable: str = "godot",
    output_path: Path | None = None,
) -> Path:
    """Generate extension_api.json from a local Godot installation.

    If output_path is None, the version is queried from the executable and the
    file is written to the versioned cache path (e.g. extension_api_4_3.json).
    """
    if output_path is None:
        version = _godot_version_string(godot_executable)
        output_path = _versioned_api_path(version) if version else _legacy_api_path()

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Godot writes extension_api.json into cwd, so we work in a temp location
    # then move the result to the final path.
    result = subprocess.run(
        [godot_executable, "--headless", "--dump-extension-api"],
        capture_output=True,
        text=True,
        cwd=str(output_path.parent),
    )
    if result.returncode != 0:
        raise RuntimeError(f"Godot exited with code {result.returncode}:\n{result.stderr}")

    generated = output_path.parent / "extension_api.json"
    if generated != output_path:
        generated.rename(output_path)

    return output_path


# ---------------------------------------------------------------------------
# Project version detection
# ---------------------------------------------------------------------------


def _detect_project_version() -> str | None:
    """Read the Godot version requirement from the current project's project.godot.

    Returns a 'major.minor' string (e.g. '4.3') or None if unavailable.
    """
    try:
        from godot_mcp.config import get_project_root
        from godot_mcp.parsers.project_config import get_godot_version, parse_project_config

        root = get_project_root()
        config = parse_project_config(root / "project.godot")
        version = get_godot_version(config)
        return version or None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Index loading with auto-generation
# ---------------------------------------------------------------------------


def _load_index(version: str | None) -> dict[str, dict[str, Any]]:
    """Load (and cache) the class index for the given version.

    If the data file doesn't exist, attempts to auto-generate it by finding
    the Godot executable. Raises FileNotFoundError if generation is impossible.
    """
    cache_key = version or "legacy"
    if cache_key in _index_cache:
        return _index_cache[cache_key]

    path = _versioned_api_path(version) if version else _legacy_api_path()

    # Try to auto-generate if the file is missing
    if not path.exists():
        godot = _find_godot_executable()
        if godot:
            try:
                actual_path = generate_extension_api(godot, output_path=path)
                path = actual_path
            except Exception:
                pass

    # Also accept the legacy unversioned file as a fallback for any version
    if not path.exists() and version and _legacy_api_path().exists():
        path = _legacy_api_path()

    if not path.exists():
        raise FileNotFoundError(
            f"No classdata found for Godot {version or '(unknown)'}.\n"
            "Run: uv run generate-classdata\n"
            "Or: GODOT_EXECUTABLE=/path/to/godot uv run generate-classdata"
        )

    with path.open(encoding="utf-8") as f:
        api = json.load(f)

    index: dict[str, dict[str, Any]] = {
        cls["name"]: cls for cls in api.get("classes", []) if "name" in cls
    }
    _index_cache[cache_key] = index
    return index


def _get_index() -> dict[str, dict[str, Any]]:
    """Return the class index for the currently configured project."""
    version = _detect_project_version()
    return _load_index(version)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_class(class_name: str) -> dict[str, Any] | None:
    """Get full class info by name."""
    try:
        return _get_index().get(class_name)
    except FileNotFoundError:
        return None


def get_class_summary(class_name: str) -> dict[str, Any] | None:
    """Get a compact class summary with methods, properties, signals, and inheritance."""
    cls = get_class(class_name)
    if cls is None:
        return None

    return {
        "name": cls.get("name"),
        "inherits": cls.get("inherits"),
        "properties": [
            {
                "name": p.get("name"),
                "type": p.get("type"),
                "default_value": p.get("default_value"),
            }
            for p in cls.get("properties", [])
        ],
        "methods": [
            {
                "name": m.get("name"),
                "return_type": m.get("return_value", {}).get("type")
                if m.get("return_value")
                else "void",
                "arguments": [
                    {"name": a.get("name"), "type": a.get("type")} for a in m.get("arguments", [])
                ],
            }
            for m in cls.get("methods", [])
        ],
        "signals": [
            {
                "name": s.get("name"),
                "arguments": [
                    {"name": a.get("name"), "type": a.get("type")} for a in s.get("arguments", [])
                ],
            }
            for s in cls.get("signals", [])
        ],
        "constants": [
            {"name": c.get("name"), "value": c.get("value")} for c in cls.get("constants", [])
        ],
    }


def list_classes() -> list[str]:
    """Return a sorted list of all known class names."""
    try:
        return sorted(_get_index().keys())
    except FileNotFoundError:
        return []


def get_inheritance_chain(class_name: str) -> list[str]:
    """Return the full inheritance chain from class_name up to Object."""
    try:
        idx = _get_index()
    except FileNotFoundError:
        return [class_name]

    chain = [class_name]
    current = class_name
    while True:
        cls = idx.get(current)
        if not cls:
            break
        parent = cls.get("inherits")
        if not parent:
            break
        chain.append(parent)
        current = parent
    return chain


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def _generate_cli() -> None:
    """CLI entry point for `uv run generate-classdata`."""
    import os

    godot = os.environ.get("GODOT_EXECUTABLE")
    if godot:
        print(f"Using GODOT_EXECUTABLE: {godot}")
    else:
        godot = _find_godot_executable()
        if godot:
            print(f"Found Godot at: {godot}")
        else:
            print(
                "Error: Godot executable not found.\n"
                "Install Godot 4 or set GODOT_EXECUTABLE=/path/to/godot",
                file=sys.stderr,
            )
            sys.exit(1)

    version = _godot_version_string(godot)
    if version:
        print(f"Detected Godot version: {version}")
    else:
        print("Warning: could not detect Godot version, using legacy path", file=sys.stderr)

    try:
        path = generate_extension_api(godot)
        print(f"Generated: {path}")
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
