"""Parser for Godot 4 project.godot files.

project.godot uses an INI-like format with Godot-typed values:
  [section]
  key="string"
  key=1
  key=Vector2(0, 0)
  key=PackedStringArray("a", "b")
"""

from __future__ import annotations

import configparser
import re
from pathlib import Path
from typing import Any

from godot_mcp.parsers.values import parse_value


def parse_project_config(path: Path) -> dict[str, Any]:
    """Parse a project.godot file and return a nested dict of sections and values."""
    text = path.read_text(encoding="utf-8")
    return parse_project_config_text(text)


def parse_project_config_text(text: str) -> dict[str, Any]:
    """Parse project.godot text content."""
    # Godot's config format is INI-like but the first line is a config version marker:
    # ; Engine configuration file.
    # ; It's best edited using the editor UI and not directly,
    # ; since the parameters that go here are not all obvious.
    #
    # [configuration]
    # config_version=5
    #
    # We handle it via configparser with some preprocessing.

    result: dict[str, Any] = {}
    current_section = ""

    for line in text.splitlines():
        stripped = line.strip()

        # Skip comments and empty lines
        if not stripped or stripped.startswith(";"):
            continue

        # Section header
        m = re.match(r"^\[([^\]]+)\]$", stripped)
        if m:
            current_section = m.group(1)
            result.setdefault(current_section, {})
            continue

        # Key = value
        m = re.match(r'^([A-Za-z_][A-Za-z0-9_/]*)\s*=\s*(.+)$', stripped)
        if m:
            key = m.group(1)
            raw = m.group(2)
            try:
                value = parse_value(raw)
            except Exception:
                value = raw
            if current_section:
                result[current_section][key] = value
            else:
                result.setdefault("", {})[key] = value

    return result


def get_project_name(config: dict[str, Any]) -> str:
    """Extract the project name from parsed config."""
    return config.get("application", {}).get("config/name", "")


def get_main_scene(config: dict[str, Any]) -> str:
    """Extract the main scene path from parsed config."""
    val = config.get("application", {}).get("run/main_scene", "")
    if isinstance(val, str):
        return val
    return str(val)


def get_autoloads(config: dict[str, Any]) -> dict[str, str]:
    """Extract autoload singletons as {name: path} dict."""
    autoloads: dict[str, str] = {}
    raw = config.get("autoload", {})
    for name, val in raw.items():
        # Values are like "*res://scripts/MyAutoload.gd" (star = singleton)
        if isinstance(val, str):
            path = val.lstrip("*")
        else:
            path = str(val)
        autoloads[name] = path
    return autoloads


def get_godot_version(config: dict[str, Any]) -> str:
    """Try to extract the Godot version requirement."""
    return config.get("", {}).get("config_version", "")
