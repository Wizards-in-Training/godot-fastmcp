"""Parser and serializer for Godot 4 .tscn and .tres files (format=3).

TSCN structure:
  [gd_scene format=3 uid="uid://..." load_steps=N]
  [ext_resource type="..." uid="..." path="res://..." id="..."]
  [sub_resource type="..." id="..."]
  key = value
  [node name="..." type="..." parent="..."]
  key = value
  [connection signal="..." from="..." to="..." method="..."]

TRES structure: same but header is [gd_resource type="..." ...]
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from godot_mcp.parsers.values import parse_value, value_to_string


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class ExtResource:
    type: str
    path: str
    id: str
    uid: str = ""

    def to_tscn(self) -> str:
        uid_part = f' uid="{self.uid}"' if self.uid else ""
        return f'[ext_resource type="{self.type}"{uid_part} path="{self.path}" id="{self.id}"]'


@dataclass
class SubResource:
    type: str
    id: str
    properties: dict[str, Any] = field(default_factory=dict)

    def to_tscn(self) -> str:
        lines = [f'[sub_resource type="{self.type}" id="{self.id}"]']
        for k, v in self.properties.items():
            lines.append(f"{k} = {value_to_string(v)}")
        lines.append("")
        return "\n".join(lines)


@dataclass
class Node:
    name: str
    type: str | None = None
    parent: str | None = None
    instance: str | None = None  # res:// path if this node instances a scene
    instance_id: str | None = None  # ExtResource id for the instanced scene
    properties: dict[str, Any] = field(default_factory=dict)
    groups: list[str] = field(default_factory=list)

    def node_path(self) -> str:
        """Return the node path (e.g. 'Player/Sprite2D')."""
        if self.parent is None or self.parent == ".":
            return self.name
        if self.parent == "":
            return self.name
        return f"{self.parent}/{self.name}"

    def to_tscn(self) -> str:
        attrs: list[str] = [f'name="{self.name}"']
        if self.type:
            attrs.append(f'type="{self.type}"')
        if self.parent is not None:
            attrs.append(f'parent="{self.parent}"')
        if self.instance_id:
            attrs.append(f'instance=ExtResource("{self.instance_id}")')
        if self.groups:
            groups_str = ", ".join(f'"{g}"' for g in self.groups)
            attrs.append(f"groups=[{groups_str}]")
        header = "[node " + " ".join(attrs) + "]"
        lines = [header]
        for k, v in self.properties.items():
            lines.append(f"{k} = {value_to_string(v)}")
        lines.append("")
        return "\n".join(lines)


@dataclass
class Connection:
    signal: str
    from_node: str
    to_node: str
    method: str
    binds: list[Any] = field(default_factory=list)
    flags: int = 0

    def to_tscn(self) -> str:
        attrs = [
            f'signal="{self.signal}"',
            f'from="{self.from_node}"',
            f'to="{self.to_node}"',
            f'method="{self.method}"',
        ]
        if self.binds:
            binds_str = "[" + ", ".join(value_to_string(b) for b in self.binds) + "]"
            attrs.append(f"binds={binds_str}")
        if self.flags:
            attrs.append(f"flags={self.flags}")
        return "[connection " + " ".join(attrs) + "]"


@dataclass
class TscnFile:
    """Represents a parsed .tscn or .tres file."""
    # Header attributes (load_steps, uid, etc.)
    header_attrs: dict[str, str] = field(default_factory=dict)
    is_resource: bool = False  # True for .tres files
    resource_type: str | None = None  # For .tres: the resource type

    ext_resources: list[ExtResource] = field(default_factory=list)
    sub_resources: list[SubResource] = field(default_factory=list)
    nodes: list[Node] = field(default_factory=list)
    connections: list[Connection] = field(default_factory=list)

    # For .tres: top-level resource properties
    resource_properties: dict[str, Any] = field(default_factory=dict)

    def get_node(self, path: str) -> Node | None:
        """Get a node by its path (e.g. '.' for root, 'Child', 'Parent/Child')."""
        if path == ".":
            return self.nodes[0] if self.nodes else None
        for node in self.nodes:
            if node.node_path() == path or node.name == path:
                return node
        return None

    def get_root_node(self) -> Node | None:
        return self.nodes[0] if self.nodes else None

    def to_tscn(self) -> str:
        lines: list[str] = []

        # Header
        if self.is_resource:
            rtype = f' type="{self.resource_type}"' if self.resource_type else ""
            extra = _format_header_attrs(self.header_attrs, exclude={"type"})
            lines.append(f"[gd_resource{rtype}{extra}]")
        else:
            extra = _format_header_attrs(self.header_attrs)
            lines.append(f"[gd_scene{extra}]")
        lines.append("")

        # External resources
        for er in self.ext_resources:
            lines.append(er.to_tscn())
        if self.ext_resources:
            lines.append("")

        # Sub-resources
        for sr in self.sub_resources:
            lines.append(sr.to_tscn())

        # Nodes (scene only)
        for node in self.nodes:
            lines.append(node.to_tscn())

        # Resource properties (tres only)
        if self.resource_properties:
            for k, v in self.resource_properties.items():
                lines.append(f"{k} = {value_to_string(v)}")
            lines.append("")

        # Connections
        for conn in self.connections:
            lines.append(conn.to_tscn())
        if self.connections:
            lines.append("")

        return "\n".join(lines)


def _format_header_attrs(attrs: dict[str, str], exclude: set[str] | None = None) -> str:
    exclude = exclude or set()
    parts = []
    for k, v in attrs.items():
        if k in exclude:
            continue
        # Numbers don't get quotes; strings do
        if re.match(r"^[0-9]+$", v):
            parts.append(f" {k}={v}")
        else:
            parts.append(f' {k}="{v}"')
    return "".join(parts)


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

# Matches a section header like [gd_scene format=3 uid="uid://abc" load_steps=5]
_SECTION_RE = re.compile(r"^\[([^\]]+)\]$")
# Matches key = value (possibly with spaces around =)
_KV_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_/]*)\s*=\s*(.+)$")
# Header attribute: key="value" or key=number
_HEADER_ATTR_RE = re.compile(r'(\w+)=(?:"([^"]*)"|(\S+?)(?=\s+\w+=|\s*$|\]))')


def parse_tscn(text: str) -> TscnFile:
    """Parse a .tscn or .tres file from its text content."""
    lines = text.splitlines()
    result = TscnFile()

    current_section: str | None = None
    current_attrs: dict[str, str] = {}
    current_properties: dict[str, Any] = {}

    def flush_section() -> None:
        nonlocal current_section, current_attrs, current_properties
        if current_section is None:
            return
        _process_section(result, current_section, current_attrs, current_properties)
        current_section = None
        current_attrs = {}
        current_properties = {}

    i = 0
    while i < len(lines):
        line = lines[i].rstrip()

        # Skip empty lines and comments
        if not line or line.startswith(";"):
            i += 1
            continue

        # Section header
        m = _SECTION_RE.match(line)
        if m:
            flush_section()
            section_content = m.group(1)
            current_section, current_attrs = _parse_section_header(section_content)
            current_properties = {}
            i += 1
            continue

        # Key-value pair (may span multiple lines for multiline values)
        m = _KV_RE.match(line)
        if m and current_section is not None:
            key = m.group(1)
            raw_value = m.group(2)

            # Multiline: if brackets/braces are unbalanced, consume more lines
            while _is_incomplete(raw_value) and i + 1 < len(lines):
                i += 1
                raw_value += "\n" + lines[i].rstrip()

            try:
                current_properties[key] = parse_value(raw_value)
            except Exception:
                # Store as raw string if parsing fails
                current_properties[key] = raw_value

            i += 1
            continue

        i += 1

    flush_section()
    return result


def _is_incomplete(s: str) -> bool:
    """Check if brackets/braces/quotes are unbalanced (multiline value)."""
    depth = 0
    in_str = False
    str_char = ""
    for ch in s:
        if in_str:
            if ch == str_char:
                in_str = False
            elif ch == "\\":
                continue
        elif ch in ('"', "'"):
            in_str = True
            str_char = ch
        elif ch in ("[", "{", "("):
            depth += 1
        elif ch in ("]", "}", ")"):
            depth -= 1
    return depth != 0 or in_str


def _parse_section_header(content: str) -> tuple[str, dict[str, str]]:
    """Parse a section header string into (section_type, attrs_dict)."""
    parts = content.split(None, 1)
    section_type = parts[0]
    attrs: dict[str, str] = {}

    if len(parts) > 1:
        for m in _HEADER_ATTR_RE.finditer(parts[1]):
            key = m.group(1)
            val = m.group(2) if m.group(2) is not None else m.group(3)
            attrs[key] = val

    return section_type, attrs


def _process_section(
    result: TscnFile,
    section: str,
    attrs: dict[str, str],
    properties: dict[str, Any],
) -> None:
    if section == "gd_scene":
        result.header_attrs = {k: v for k, v in attrs.items() if k != "format"}
        if "format" in attrs:
            result.header_attrs["format"] = attrs["format"]

    elif section == "gd_resource":
        result.is_resource = True
        result.resource_type = attrs.get("type")
        result.header_attrs = {k: v for k, v in attrs.items() if k != "type"}
        result.resource_properties = properties

    elif section == "ext_resource":
        er = ExtResource(
            type=attrs.get("type", ""),
            uid=attrs.get("uid", ""),
            path=attrs.get("path", ""),
            id=attrs.get("id", ""),
        )
        result.ext_resources.append(er)

    elif section == "sub_resource":
        sr = SubResource(
            type=attrs.get("type", ""),
            id=attrs.get("id", ""),
            properties=properties,
        )
        result.sub_resources.append(sr)

    elif section == "node":
        # Extract instance from properties if present as ExtResource ref
        from godot_mcp.parsers.values import ExtResourceRef

        instance_prop = properties.pop("instance", None)
        instance_id = None
        if isinstance(instance_prop, ExtResourceRef):
            instance_id = instance_prop.id

        # Groups may appear as an attribute or a property
        groups_raw = attrs.get("groups", "")
        groups: list[str] = []
        if groups_raw:
            groups = [g.strip().strip('"') for g in groups_raw.strip("[]").split(",") if g.strip()]

        node = Node(
            name=attrs.get("name", ""),
            type=attrs.get("type") or None,
            parent=attrs.get("parent") or None,
            instance_id=instance_id,
            properties=properties,
            groups=groups,
        )
        result.nodes.append(node)

    elif section == "connection":
        binds_raw = attrs.get("binds", "[]")
        try:
            binds = parse_value(binds_raw)
            if not isinstance(binds, list):
                binds = []
        except Exception:
            binds = []

        conn = Connection(
            signal=attrs.get("signal", ""),
            from_node=attrs.get("from", ""),
            to_node=attrs.get("to", ""),
            method=attrs.get("method", ""),
            binds=binds,
            flags=int(attrs.get("flags", "0")),
        )
        result.connections.append(conn)


def parse_tres(text: str) -> TscnFile:
    """Parse a .tres file. Same format as TSCN but with gd_resource header."""
    return parse_tscn(text)


def tscn_to_dict(tscn: TscnFile) -> dict[str, Any]:
    """Convert a TscnFile to a JSON-serializable dict for MCP tool responses."""
    return {
        "is_resource": tscn.is_resource,
        "resource_type": tscn.resource_type,
        "header": tscn.header_attrs,
        "ext_resources": [
            {"id": er.id, "type": er.type, "path": er.path, "uid": er.uid}
            for er in tscn.ext_resources
        ],
        "sub_resources": [
            {"id": sr.id, "type": sr.type, "properties": _serialize_props(sr.properties)}
            for sr in tscn.sub_resources
        ],
        "nodes": [
            {
                "name": n.name,
                "type": n.type,
                "parent": n.parent,
                "path": n.node_path(),
                "instance_id": n.instance_id,
                "groups": n.groups,
                "properties": _serialize_props(n.properties),
            }
            for n in tscn.nodes
        ],
        "connections": [
            {
                "signal": c.signal,
                "from": c.from_node,
                "to": c.to_node,
                "method": c.method,
                "binds": c.binds,
            }
            for c in tscn.connections
        ],
        "resource_properties": _serialize_props(tscn.resource_properties),
    }


def _serialize_props(props: dict[str, Any]) -> dict[str, Any]:
    """Convert property values to JSON-safe representations."""
    result = {}
    for k, v in props.items():
        result[k] = _serialize_value(v)
    return result


def _serialize_value(v: Any) -> Any:
    if v is None or isinstance(v, (bool, int, float, str)):
        return v
    if isinstance(v, list):
        return [_serialize_value(i) for i in v]
    if isinstance(v, dict):
        return {str(k): _serialize_value(val) for k, val in v.items()}
    # Godot types — convert to string representation
    return str(v)
