"""Parse Godot 4 literal value types from .tscn and .tres files.

Handles: Vector2/3/4, Rect2, Transform2D/3D, Color, Plane, Quaternion,
         AABB, Basis, Projection, NodePath, StringName, RID,
         Array, Dictionary, PackedByteArray/Int32Array/etc.,
         ExtResource, SubResource, strings, numbers, booleans, null.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

# ---------------------------------------------------------------------------
# Value types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Vector2:
    x: float
    y: float

    def __str__(self) -> str:
        return f"Vector2({_fmt(self.x)}, {_fmt(self.y)})"


@dataclass(frozen=True)
class Vector2i:
    x: int
    y: int

    def __str__(self) -> str:
        return f"Vector2i({self.x}, {self.y})"


@dataclass(frozen=True)
class Vector3:
    x: float
    y: float
    z: float

    def __str__(self) -> str:
        return f"Vector3({_fmt(self.x)}, {_fmt(self.y)}, {_fmt(self.z)})"


@dataclass(frozen=True)
class Vector3i:
    x: int
    y: int
    z: int

    def __str__(self) -> str:
        return f"Vector3i({self.x}, {self.y}, {self.z})"


@dataclass(frozen=True)
class Vector4:
    x: float
    y: float
    z: float
    w: float

    def __str__(self) -> str:
        return f"Vector4({_fmt(self.x)}, {_fmt(self.y)}, {_fmt(self.z)}, {_fmt(self.w)})"


@dataclass(frozen=True)
class Vector4i:
    x: int
    y: int
    z: int
    w: int

    def __str__(self) -> str:
        return f"Vector4i({self.x}, {self.y}, {self.z}, {self.w})"


@dataclass(frozen=True)
class Rect2:
    x: float
    y: float
    width: float
    height: float

    def __str__(self) -> str:
        return f"Rect2({_fmt(self.x)}, {_fmt(self.y)}, {_fmt(self.width)}, {_fmt(self.height)})"


@dataclass(frozen=True)
class Rect2i:
    x: int
    y: int
    width: int
    height: int

    def __str__(self) -> str:
        return f"Rect2i({self.x}, {self.y}, {self.width}, {self.height})"


@dataclass(frozen=True)
class Color:
    r: float
    g: float
    b: float
    a: float = 1.0

    def __str__(self) -> str:
        return f"Color({_fmt(self.r)}, {_fmt(self.g)}, {_fmt(self.b)}, {_fmt(self.a)})"


@dataclass(frozen=True)
class Plane:
    x: float
    y: float
    z: float
    d: float

    def __str__(self) -> str:
        return f"Plane({_fmt(self.x)}, {_fmt(self.y)}, {_fmt(self.z)}, {_fmt(self.d)})"


@dataclass(frozen=True)
class Quaternion:
    x: float
    y: float
    z: float
    w: float

    def __str__(self) -> str:
        return f"Quaternion({_fmt(self.x)}, {_fmt(self.y)}, {_fmt(self.z)}, {_fmt(self.w)})"


@dataclass(frozen=True)
class AABB:
    position: Vector3
    size: Vector3

    def __str__(self) -> str:
        p, s = self.position, self.size
        args = ", ".join(_fmt(v) for v in [p.x, p.y, p.z, s.x, s.y, s.z])
        return f"AABB({args})"


@dataclass(frozen=True)
class Basis:
    values: tuple[float, ...]

    def __str__(self) -> str:
        return f"Basis({', '.join(_fmt(v) for v in self.values)})"


@dataclass(frozen=True)
class Transform2D:
    values: tuple[float, ...]

    def __str__(self) -> str:
        return f"Transform2D({', '.join(_fmt(v) for v in self.values)})"


@dataclass(frozen=True)
class Transform3D:
    values: tuple[float, ...]

    def __str__(self) -> str:
        return f"Transform3D({', '.join(_fmt(v) for v in self.values)})"


@dataclass(frozen=True)
class Projection:
    values: tuple[float, ...]

    def __str__(self) -> str:
        return f"Projection({', '.join(_fmt(v) for v in self.values)})"


@dataclass(frozen=True)
class NodePath:
    path: str

    def __str__(self) -> str:
        return f'NodePath("{self.path}")'


@dataclass(frozen=True)
class StringName:
    name: str

    def __str__(self) -> str:
        return f'&"{self.name}"'


@dataclass(frozen=True)
class ExtResourceRef:
    id: str

    def __str__(self) -> str:
        return f'ExtResource("{self.id}")'


@dataclass(frozen=True)
class SubResourceRef:
    id: str

    def __str__(self) -> str:
        return f'SubResource("{self.id}")'


@dataclass(frozen=True)
class PackedArray:
    type_name: str
    values: tuple[Any, ...]

    def __str__(self) -> str:
        if not self.values:
            return f"{self.type_name}()"
        args = ", ".join(_fmt(v) for v in self.values)
        return f"{self.type_name}({args})"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fmt(v: Any) -> str:
    """Format a value for TSCN serialization (numbers, strings, and other types)."""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        if v == int(v) and abs(v) < 1e15:
            return str(int(v))
        return repr(v)
    if isinstance(v, str):
        escaped = v.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return str(v)


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


class _Scanner:
    def __init__(self, text: str) -> None:
        self.text = text
        self.pos = 0

    @property
    def done(self) -> bool:
        return self.pos >= len(self.text)

    def peek(self, n: int = 1) -> str:
        return self.text[self.pos : self.pos + n]

    def consume(self, n: int = 1) -> str:
        result = self.text[self.pos : self.pos + n]
        self.pos += n
        return result

    def skip_ws(self) -> None:
        while not self.done and self.text[self.pos] in " \t\r\n":
            self.pos += 1

    def expect(self, ch: str) -> None:
        self.skip_ws()
        got = self.peek(len(ch))
        if got != ch:
            raise ValueError(
                f"Expected {ch!r} at pos {self.pos}, got {got!r}. "
                f"Context: {self.text[max(0, self.pos - 20) : self.pos + 20]!r}"
            )
        self.consume(len(ch))

    def match_re(self, pattern: str) -> re.Match | None:
        self.skip_ws()
        m = re.match(pattern, self.text[self.pos :])
        if m:
            self.pos += m.end()
        return m


def parse_value(text: str) -> Any:
    """Parse a single Godot value expression from a string."""
    scanner = _Scanner(text.strip())
    return _parse_expr(scanner)


def _parse_expr(sc: _Scanner) -> Any:
    sc.skip_ws()
    if sc.done:
        return None

    # Keywords: null, true, false
    for kw, val in [("null", None), ("true", True), ("false", False)]:
        if sc.text[sc.pos :].startswith(kw):
            rest = sc.text[sc.pos + len(kw) :]
            if not rest or not (rest[0].isalnum() or rest[0] == "_"):
                sc.consume(len(kw))
                return val

    # StringName &"..."
    if sc.peek() == "&":
        sc.consume(1)
        return StringName(_parse_string(sc))

    # String
    if sc.peek() in ('"', "'"):
        return _parse_string(sc)

    # Number
    m = sc.match_re(r"-?(?:inf|nan|0x[0-9a-fA-F]+|[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?)")
    if m:
        raw = m.group(0)
        if raw in ("inf", "-inf", "nan"):
            return float(raw)
        if "." in raw or "e" in raw.lower():
            return float(raw)
        if raw.startswith("0x"):
            return int(raw, 16)
        return int(raw)

    # Array
    if sc.peek() == "[":
        return _parse_array(sc)

    # Dictionary
    if sc.peek() == "{":
        return _parse_dict(sc)

    # Named constructor
    m = sc.match_re(r"([A-Za-z_][A-Za-z0-9_]*)\s*\(")
    if m:
        name = m.group(1)
        args = _parse_args(sc)
        return _build_named(name, args)

    raise ValueError(f"Cannot parse value at pos {sc.pos}: {sc.text[sc.pos : sc.pos + 40]!r}")


def _parse_string(sc: _Scanner) -> str:
    sc.skip_ws()
    quote = sc.consume()
    parts: list[str] = []
    while not sc.done:
        ch = sc.consume()
        if ch == "\\":
            esc = sc.consume()
            parts.append(
                {"n": "\n", "t": "\t", "r": "\r", "\\": "\\", '"': '"', "'": "'", "0": "\0"}.get(
                    esc, esc
                )
            )
        elif ch == quote:
            break
        else:
            parts.append(ch)
    return "".join(parts)


def _parse_array(sc: _Scanner) -> list[Any]:
    sc.expect("[")
    items: list[Any] = []
    sc.skip_ws()
    while not sc.done and sc.peek() != "]":
        items.append(_parse_expr(sc))
        sc.skip_ws()
        if sc.peek() == ",":
            sc.consume()
    sc.expect("]")
    return items


def _parse_dict(sc: _Scanner) -> dict[Any, Any]:
    sc.expect("{")
    result: dict[Any, Any] = {}
    sc.skip_ws()
    while not sc.done and sc.peek() != "}":
        key = _parse_expr(sc)
        sc.skip_ws()
        sc.expect(":")
        val = _parse_expr(sc)
        result[key] = val
        sc.skip_ws()
        if sc.peek() == ",":
            sc.consume()
        sc.skip_ws()
    sc.expect("}")
    return result


def _parse_args(sc: _Scanner) -> list[Any]:
    """Parse comma-separated args until ')'. Opening '(' was consumed by match_re."""
    args: list[Any] = []
    sc.skip_ws()
    while not sc.done and sc.peek() != ")":
        args.append(_parse_expr(sc))
        sc.skip_ws()
        if sc.peek() == ",":
            sc.consume()
    sc.expect(")")
    return args


def _build_named(name: str, args: list[Any]) -> Any:
    # Handle string-arg types before attempting numeric conversion
    match name:
        case "NodePath":
            return NodePath(args[0] if args else "")
        case "ExtResource":
            return ExtResourceRef(str(args[0]) if args else "")
        case "SubResource":
            return SubResourceRef(str(args[0]) if args else "")

    # For numeric types, try float/int conversion
    try:
        floats = [float(a) for a in args] if args else []
        ints = [int(float(a)) for a in args] if args else []
    except (TypeError, ValueError):
        # Fallback: return as generic packed array
        return PackedArray(name, tuple(args))

    match name:
        case "Vector2":
            return Vector2(*floats)
        case "Vector2i":
            return Vector2i(*ints)
        case "Vector3":
            return Vector3(*floats)
        case "Vector3i":
            return Vector3i(*ints)
        case "Vector4":
            return Vector4(*floats)
        case "Vector4i":
            return Vector4i(*ints)
        case "Rect2":
            return Rect2(*floats)
        case "Rect2i":
            return Rect2i(*ints)
        case "Color":
            return Color(*floats)
        case "Plane":
            return Plane(*floats)
        case "Quaternion":
            return Quaternion(*floats)
        case "AABB":
            pos = Vector3(floats[0], floats[1], floats[2])
            size = Vector3(floats[3], floats[4], floats[5])
            return AABB(pos, size)
        case "Basis":
            return Basis(tuple(floats))
        case "Transform2D":
            return Transform2D(tuple(floats))
        case "Transform3D":
            return Transform3D(tuple(floats))
        case "Projection":
            return Projection(tuple(floats))
        case _:
            return PackedArray(name, tuple(args))


def value_to_string(value: Any) -> str:
    """Serialize a Python value back to Godot TSCN string format."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return _fmt(value)
    if isinstance(value, str):
        escaped = (
            value.replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("\n", "\\n")
            .replace("\t", "\\t")
        )
        return f'"{escaped}"'
    if isinstance(value, list):
        if not value:
            return "[]"
        return "[" + ", ".join(value_to_string(v) for v in value) + "]"
    if isinstance(value, dict):
        if not value:
            return "{}"
        pairs = ", ".join(f"{value_to_string(k)}: {value_to_string(v)}" for k, v in value.items())
        return "{" + pairs + "}"
    return str(value)
