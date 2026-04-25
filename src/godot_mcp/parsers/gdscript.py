"""Wrapper around gdtoolkit for GDScript linting and formatting."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


def validate_gdscript(source: str, filename: str = "<string>") -> list[dict[str, Any]]:
    """Lint GDScript source using gdtoolkit.

    Returns a list of diagnostics: [{"line": int, "column": int, "message": str, "severity": str}]
    """
    with tempfile.NamedTemporaryFile(suffix=".gd", mode="w", encoding="utf-8", delete=False) as f:
        f.write(source)
        tmp_path = f.name

    try:
        result = subprocess.run(
            [sys.executable, "-m", "gdtoolkit.gdlint", tmp_path],
            capture_output=True,
            text=True,
        )
        diagnostics = _parse_gdlint_output(result.stdout + result.stderr)
        return diagnostics
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def validate_gdscript_file(path: Path) -> list[dict[str, Any]]:
    """Lint a GDScript file."""
    result = subprocess.run(
        [sys.executable, "-m", "gdtoolkit.gdlint", str(path)],
        capture_output=True,
        text=True,
    )
    return _parse_gdlint_output(result.stdout + result.stderr)


def format_gdscript(source: str) -> str:
    """Format GDScript source using gdtoolkit's formatter."""
    with tempfile.NamedTemporaryFile(suffix=".gd", mode="w", encoding="utf-8", delete=False) as f:
        f.write(source)
        tmp_path = f.name

    try:
        subprocess.run(
            [sys.executable, "-m", "gdtoolkit.gdformat", tmp_path],
            capture_output=True,
            text=True,
            check=False,
        )
        return Path(tmp_path).read_text(encoding="utf-8")
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def format_gdscript_file(path: Path) -> None:
    """Format a GDScript file in-place."""
    subprocess.run(
        [sys.executable, "-m", "gdtoolkit.gdformat", str(path)],
        capture_output=True,
        text=True,
        check=False,
    )


def _parse_gdlint_output(output: str) -> list[dict[str, Any]]:
    """Parse gdlint output into structured diagnostics."""
    import re

    diagnostics = []
    # gdlint outputs lines like: path/to/file.gd:10: error message (rule-name)
    pattern = re.compile(r"^.+?:(\d+):\s+(.+)$", re.MULTILINE)
    for m in pattern.finditer(output):
        line = int(m.group(1))
        message = m.group(2).strip()
        severity = "error" if "error" in message.lower() else "warning"
        diagnostics.append(
            {
                "line": line,
                "column": 0,
                "message": message,
                "severity": severity,
            }
        )
    return diagnostics
