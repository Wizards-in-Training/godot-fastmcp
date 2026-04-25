"""Loads and indexes Godot's extension_api.json for class reference lookups."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

_DATA_DIR = Path(__file__).parent / "data"
_API_PATH = _DATA_DIR / "extension_api.json"

_index: dict[str, dict[str, Any]] | None = None


def get_api_path() -> Path:
    return _API_PATH


def generate_extension_api(
    godot_executable: str = "godot", output_path: Path | None = None
) -> Path:
    """Generate extension_api.json from a local Godot installation.

    Runs: godot --headless --dump-extension-api
    """
    out = output_path or _API_PATH
    out.parent.mkdir(parents=True, exist_ok=True)

    result = subprocess.run(
        [godot_executable, "--headless", "--dump-extension-api"],
        capture_output=True,
        text=True,
        cwd=str(out.parent),
    )
    if result.returncode != 0:
        raise RuntimeError(f"Failed to generate extension_api.json:\n{result.stderr}")

    # Godot writes extension_api.json in the cwd
    generated = out.parent / "extension_api.json"
    if generated != out:
        generated.rename(out)

    return out


def _load_index() -> dict[str, dict[str, Any]]:
    global _index
    if _index is not None:
        return _index

    if not _API_PATH.exists():
        raise FileNotFoundError(
            f"extension_api.json not found at {_API_PATH}.\n"
            "Run: uv run generate-classdata\n"
            "Or set GODOT_EXECUTABLE and call generate_extension_api()."
        )

    with _API_PATH.open(encoding="utf-8") as f:
        api = json.load(f)

    index: dict[str, dict[str, Any]] = {}
    for cls in api.get("classes", []):
        name = cls.get("name", "")
        index[name] = cls

    _index = index
    return _index


def get_class(class_name: str) -> dict[str, Any] | None:
    """Get full class info by name."""
    try:
        return _load_index().get(class_name)
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
        return sorted(_load_index().keys())
    except FileNotFoundError:
        return []


def _generate_cli() -> None:
    """CLI entry point for generate-classdata script."""
    import os

    godot = os.environ.get("GODOT_EXECUTABLE", "godot")
    print(f"Generating extension_api.json using: {godot}")
    try:
        path = generate_extension_api(godot)
        print(f"Generated: {path}")
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def get_inheritance_chain(class_name: str) -> list[str]:
    """Return the full inheritance chain from class_name up to Object."""
    idx = _load_index()
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
