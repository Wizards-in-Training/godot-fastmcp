"""Reusable prompt templates for Godot development."""

from __future__ import annotations

from fastmcp import FastMCP

mcp = FastMCP("prompts")


@mcp.prompt()
def gdscript_template(
    node_type: str,
    class_name: str | None = None,
    description: str = "",
) -> str:
    """Generate a GDScript class skeleton for a given Godot node type.

    Args:
        node_type: The Godot base class to extend (e.g. "CharacterBody2D", "Area2D").
        class_name: Optional class_name for the script.
        description: Brief description of what this script should do.
    """
    class_line = f"class_name {class_name}\n" if class_name else ""
    desc_line = f"# {description}\n" if description else ""

    # Provide appropriate lifecycle methods based on node type
    if "CharacterBody" in node_type:
        lifecycle = '''
func _ready() -> void:
\tpass


func _physics_process(delta: float) -> void:
\t# Add movement logic here
\tvar velocity_local := velocity
\t
\t# Apply gravity
\tif not is_on_floor():
\t\tvelocity_local += get_gravity() * delta
\t
\tmove_and_slide()
'''
    elif node_type in ("Area2D", "Area3D"):
        lifecycle = '''
func _ready() -> void:
\tbody_entered.connect(_on_body_entered)
\tarea_entered.connect(_on_area_entered)


func _on_body_entered(body: Node) -> void:
\tpass


func _on_area_entered(area: Area2D) -> void:
\tpass
'''
    elif "Control" in node_type or node_type in ("Button", "Label", "Panel"):
        lifecycle = '''
func _ready() -> void:
\tpass
'''
    else:
        lifecycle = '''
func _ready() -> void:
\tpass


func _process(delta: float) -> void:
\tpass
'''

    return (
        f"Please write a GDScript script for the following:\n\n"
        f"Node type: {node_type}\n"
        + (f"Class name: {class_name}\n" if class_name else "")
        + (f"Purpose: {description}\n" if description else "")
        + f"\nUse this template as a starting point:\n\n"
        f"```gdscript\n"
        f"{class_line}"
        f"extends {node_type}\n"
        f"{desc_line}"
        f"{lifecycle}"
        f"```\n\n"
        f"Fill in the implementation based on the purpose described above. "
        f"Follow Godot 4 best practices and use typed GDScript."
    )


@mcp.prompt()
def scene_description(scene_path: str) -> str:
    """Generate a prompt to describe the purpose and structure of a scene.

    Args:
        scene_path: res:// path to the scene file.
    """
    return (
        f"Please analyze the Godot scene at `{scene_path}` and provide:\n\n"
        "1. **Purpose**: What does this scene represent in the game?\n"
        "2. **Node structure**: Describe the node hierarchy and what each major node does.\n"
        "3. **Scripts**: What scripts are attached and what do they handle?\n"
        "4. **Connections**: Are there signal connections? What do they wire up?\n"
        "5. **External resources**: What assets does this scene depend on?\n\n"
        "Use the `scene_read` tool to inspect the scene file before answering."
    )
