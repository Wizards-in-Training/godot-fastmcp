"""GDScript file tools for Godot MCP."""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from godot_mcp.config import get_project_root, resolve_project_path, to_res_path
from godot_mcp.parsers.gdscript import (
    format_gdscript,
    format_gdscript_file,
    validate_gdscript,
    validate_gdscript_file,
)

mcp = FastMCP("script")


@mcp.tool(annotations={"readOnlyHint": True})
def script_read(path: str) -> str:
    """Read the contents of a GDScript file.

    Args:
        path: Path to the .gd file (res:// format or relative to project root).

    Returns the raw GDScript source code.
    """
    root = get_project_root()
    abs_path = resolve_project_path(root, path)
    if not abs_path.exists():
        raise FileNotFoundError(f"Script file not found: {path}")
    if abs_path.suffix != ".gd":
        raise ValueError(f"Not a .gd file: {path}")
    return abs_path.read_text(encoding="utf-8")


@mcp.tool()
def script_write(path: str, content: str) -> dict[str, Any]:
    """Write or overwrite a GDScript file.

    Args:
        path: Path to the .gd file (res:// format or relative to project root).
        content: The GDScript source code to write.

    Returns info about the written file.
    """
    root = get_project_root()
    abs_path = resolve_project_path(root, path)
    if abs_path.suffix != ".gd":
        raise ValueError(f"Path must end with .gd, got: {path}")
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    abs_path.write_text(content, encoding="utf-8")
    return {
        "path": to_res_path(root, abs_path),
        "bytes_written": len(content.encode("utf-8")),
    }


@mcp.tool(annotations={"readOnlyHint": True})
def script_validate(path: str | None = None, source: str | None = None) -> list[dict[str, Any]]:
    """Validate GDScript for syntax and style issues using gdtoolkit.

    Args:
        path: Path to a .gd file to validate (res:// format). Either path or source required.
        source: Raw GDScript source to validate in-memory. Either path or source required.

    Returns a list of diagnostics: [{line, column, message, severity}].
    An empty list means no issues found.
    """
    if path is not None:
        root = get_project_root()
        abs_path = resolve_project_path(root, path)
        if not abs_path.exists():
            raise FileNotFoundError(f"Script file not found: {path}")
        return validate_gdscript_file(abs_path)
    elif source is not None:
        return validate_gdscript(source)
    else:
        raise ValueError("Either 'path' or 'source' must be provided.")


@mcp.tool()
def script_format(path: str | None = None, source: str | None = None) -> dict[str, Any]:
    """Format GDScript source using gdtoolkit's formatter.

    Args:
        path: Path to a .gd file to format in-place (res:// format).
        source: Raw GDScript source to format and return. Either path or source required.

    When path is given, the file is formatted in-place.
    When source is given, the formatted source is returned.
    """
    if path is not None:
        root = get_project_root()
        abs_path = resolve_project_path(root, path)
        if not abs_path.exists():
            raise FileNotFoundError(f"Script file not found: {path}")
        format_gdscript_file(abs_path)
        return {"path": to_res_path(root, abs_path), "formatted_in_place": True}
    elif source is not None:
        formatted = format_gdscript(source)
        return {"formatted_source": formatted}
    else:
        raise ValueError("Either 'path' or 'source' must be provided.")


@mcp.tool()
def script_create(
    path: str,
    class_name: str | None = None,
    extends: str = "Node",
    template: str = "basic",
) -> dict[str, Any]:
    """Create a new GDScript file with a starter template.

    Args:
        path: Where to create the .gd file (res:// format).
        class_name: Optional class_name declaration for the script.
        extends: The base class to extend (default: "Node").
        template: Template style - "basic" (just extends), "full" (with _ready and _process).

    Returns info about the created file.
    """
    root = get_project_root()
    abs_path = resolve_project_path(root, path)

    if abs_path.exists():
        raise FileExistsError(f"Script already exists: {path}. Use script_write to overwrite.")
    if abs_path.suffix != ".gd":
        raise ValueError(f"Path must end with .gd, got: {path}")

    lines = [f"extends {extends}", ""]
    if class_name:
        lines.insert(0, f"class_name {class_name}")
        lines.insert(1, "")
        lines[2] = f"extends {extends}"
        lines.append("")

    if template == "full":
        lines += [
            "",
            "func _ready() -> void:",
            "\tpass",
            "",
            "",
            "func _process(delta: float) -> void:",
            "\tpass",
            "",
        ]
    else:
        lines.append("")

    content = "\n".join(lines)
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    abs_path.write_text(content, encoding="utf-8")

    return {
        "path": to_res_path(root, abs_path),
        "content": content,
    }
