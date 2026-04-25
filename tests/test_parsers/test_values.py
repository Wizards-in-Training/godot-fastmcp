"""Tests for Godot value parser."""

from __future__ import annotations

import pytest

from godot_mcp.parsers.values import (
    AABB,
    Color,
    ExtResourceRef,
    NodePath,
    PackedArray,
    Rect2,
    StringName,
    SubResourceRef,
    Transform2D,
    Vector2,
    Vector3,
    parse_value,
    value_to_string,
)


class TestPrimitives:
    def test_null(self):
        assert parse_value("null") is None

    def test_true(self):
        assert parse_value("true") is True

    def test_false(self):
        assert parse_value("false") is False

    def test_integer(self):
        assert parse_value("42") == 42

    def test_negative_integer(self):
        assert parse_value("-5") == -5

    def test_float(self):
        assert parse_value("3.14") == pytest.approx(3.14)

    def test_float_scientific(self):
        assert parse_value("1e-3") == pytest.approx(0.001)

    def test_hex(self):
        assert parse_value("0xFF") == 255

    def test_string_double_quote(self):
        assert parse_value('"hello world"') == "hello world"

    def test_string_escape(self):
        assert parse_value(r'"line\nnewline"') == "line\nnewline"

    def test_string_name(self):
        result = parse_value('&"MyClass"')
        assert isinstance(result, StringName)
        assert result.name == "MyClass"


class TestContainers:
    def test_empty_array(self):
        assert parse_value("[]") == []

    def test_int_array(self):
        assert parse_value("[1, 2, 3]") == [1, 2, 3]

    def test_mixed_array(self):
        result = parse_value('[1, "hello", true, null]')
        assert result == [1, "hello", True, None]

    def test_empty_dict(self):
        assert parse_value("{}") == {}

    def test_dict(self):
        result = parse_value('{"key": "value", "num": 42}')
        assert result == {"key": "value", "num": 42}


class TestGodotTypes:
    def test_vector2(self):
        v = parse_value("Vector2(1, 2)")
        assert isinstance(v, Vector2)
        assert v.x == 1.0
        assert v.y == 2.0

    def test_vector3(self):
        v = parse_value("Vector3(1.5, 2.5, 3.5)")
        assert isinstance(v, Vector3)
        assert v.x == pytest.approx(1.5)

    def test_rect2(self):
        r = parse_value("Rect2(0, 0, 100, 200)")
        assert isinstance(r, Rect2)
        assert r.width == 100.0
        assert r.height == 200.0

    def test_color_rgba(self):
        c = parse_value("Color(1, 0.5, 0, 1)")
        assert isinstance(c, Color)
        assert c.r == 1.0
        assert c.g == pytest.approx(0.5)
        assert c.a == 1.0

    def test_node_path(self):
        np = parse_value('NodePath("Player/Sprite2D")')
        assert isinstance(np, NodePath)
        assert np.path == "Player/Sprite2D"

    def test_ext_resource(self):
        er = parse_value('ExtResource("1_abc")')
        assert isinstance(er, ExtResourceRef)
        assert er.id == "1_abc"

    def test_sub_resource(self):
        sr = parse_value('SubResource("RectangleShape2D_1")')
        assert isinstance(sr, SubResourceRef)
        assert sr.id == "RectangleShape2D_1"

    def test_transform2d(self):
        t = parse_value("Transform2D(1, 0, 0, 1, 0, 0)")
        assert isinstance(t, Transform2D)
        assert len(t.values) == 6

    def test_packed_string_array(self):
        p = parse_value('PackedStringArray("4.4", "Forward Plus")')
        assert isinstance(p, PackedArray)
        assert p.type_name == "PackedStringArray"
        assert list(p.values) == ["4.4", "Forward Plus"]

    def test_aabb(self):
        a = parse_value("AABB(0, 0, 0, 10, 20, 30)")
        assert isinstance(a, AABB)
        assert a.size.x == 10.0


class TestRoundtrip:
    def test_vector2_roundtrip(self):
        v = Vector2(1.0, 2.0)
        assert parse_value(str(v)) == v

    def test_color_roundtrip(self):
        c = Color(1.0, 0.5, 0.0, 1.0)
        assert parse_value(str(c)) == c

    def test_string_roundtrip(self):
        s = "hello\nworld"
        assert value_to_string(s) == '"hello\\nworld"'
        assert parse_value(value_to_string(s)) == s

    def test_none_roundtrip(self):
        assert value_to_string(None) == "null"

    def test_bool_roundtrip(self):
        assert value_to_string(True) == "true"
        assert value_to_string(False) == "false"

    def test_list_roundtrip(self):
        lst = [1, 2, 3]
        assert value_to_string(lst) == "[1, 2, 3]"
