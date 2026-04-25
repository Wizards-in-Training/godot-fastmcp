"""Root FastMCP server for Godot MCP."""

from __future__ import annotations

from fastmcp import FastMCP

from godot_mcp.prompts.templates import mcp as prompt_templates
from godot_mcp.resources.classref import mcp as classref_resources
from godot_mcp.resources.project import mcp as project_resources
from godot_mcp.tools.project import mcp as project_tools
from godot_mcp.tools.resource import mcp as resource_tools
from godot_mcp.tools.scene import mcp as scene_tools
from godot_mcp.tools.script import mcp as script_tools


def create_server() -> FastMCP:
    """Create and configure the Godot MCP server."""
    mcp = FastMCP(
        "Godot MCP",
        instructions=(
            "MCP server for Godot 4 game engine projects. "
            "Provides tools to inspect and modify Godot projects, scenes, scripts, "
            "and resources directly via file manipulation. "
            "Set GODOT_PROJECT_PATH to the root of your Godot 4 project before use."
        ),
    )

    mcp.mount(project_tools, namespace="")
    mcp.mount(scene_tools, namespace="")
    mcp.mount(script_tools, namespace="")
    mcp.mount(resource_tools, namespace="")
    mcp.mount(project_resources, namespace="")
    mcp.mount(classref_resources, namespace="")
    mcp.mount(prompt_templates, namespace="")

    return mcp
