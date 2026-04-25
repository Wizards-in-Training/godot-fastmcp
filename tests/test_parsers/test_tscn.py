"""Tests for TSCN parser."""

from __future__ import annotations

import pytest

from godot_mcp.parsers.tscn import (
    Connection,
    ExtResource,
    Node,
    SubResource,
    TscnFile,
    parse_tscn,
    parse_tres,
    tscn_to_dict,
)
from godot_mcp.parsers.values import ExtResourceRef, SubResourceRef, Vector2


class TestParseTscn:
    def test_parses_ext_resources(self, simple_tscn_text: str):
        tscn = parse_tscn(simple_tscn_text)
        assert len(tscn.ext_resources) == 1
        er = tscn.ext_resources[0]
        assert er.type == "Script"
        assert er.id == "1_abc"
        assert er.path == "res://scripts/player.gd"

    def test_parses_sub_resources(self, simple_tscn_text: str):
        tscn = parse_tscn(simple_tscn_text)
        assert len(tscn.sub_resources) == 1
        sr = tscn.sub_resources[0]
        assert sr.type == "RectangleShape2D"
        assert isinstance(sr.properties["size"], Vector2)
        assert sr.properties["size"].x == 20.0

    def test_parses_nodes(self, simple_tscn_text: str):
        tscn = parse_tscn(simple_tscn_text)
        assert len(tscn.nodes) == 3

    def test_root_node(self, simple_tscn_text: str):
        tscn = parse_tscn(simple_tscn_text)
        root = tscn.get_root_node()
        assert root is not None
        assert root.name == "Player"
        assert root.type == "CharacterBody2D"
        assert root.parent is None

    def test_child_nodes(self, simple_tscn_text: str):
        tscn = parse_tscn(simple_tscn_text)
        sprite = tscn.get_node("Player/Sprite2D")
        assert sprite is not None
        assert sprite.type == "Sprite2D"
        assert isinstance(sprite.properties["position"], Vector2)

    def test_node_with_script(self, simple_tscn_text: str):
        tscn = parse_tscn(simple_tscn_text)
        root = tscn.get_root_node()
        assert root is not None
        assert isinstance(root.properties.get("script"), ExtResourceRef)

    def test_parses_connections(self, simple_tscn_text: str):
        tscn = parse_tscn(simple_tscn_text)
        assert len(tscn.connections) == 1
        conn = tscn.connections[0]
        assert conn.signal == "body_entered"
        assert conn.from_node == "Player"
        assert conn.method == "_on_body_entered"

    def test_get_node_dot_returns_root(self, simple_tscn_text: str):
        tscn = parse_tscn(simple_tscn_text)
        assert tscn.get_node(".") is tscn.get_root_node()

    def test_get_node_none_for_missing(self, simple_tscn_text: str):
        tscn = parse_tscn(simple_tscn_text)
        assert tscn.get_node("NonExistent") is None

    def test_header_attrs(self, simple_tscn_text: str):
        tscn = parse_tscn(simple_tscn_text)
        assert tscn.header_attrs.get("uid") == "uid://abc123"


class TestParseTres:
    def test_parses_resource_header(self, sample_tres_text: str):
        tres = parse_tres(sample_tres_text)
        assert tres.is_resource is True

    def test_parses_resource_properties(self, sample_tres_text: str):
        tres = parse_tres(sample_tres_text)
        assert tres.resource_properties.get("max_health") == 100
        assert tres.resource_properties.get("speed") == pytest.approx(200.0)
        assert isinstance(tres.resource_properties.get("jump_height"), Vector2)


class TestSerializer:
    def test_roundtrip_preserves_nodes(self, simple_tscn_text: str):
        tscn = parse_tscn(simple_tscn_text)
        serialized = tscn.to_tscn()
        reparsed = parse_tscn(serialized)
        assert len(reparsed.nodes) == len(tscn.nodes)
        assert reparsed.get_root_node().name == tscn.get_root_node().name

    def test_roundtrip_preserves_ext_resources(self, simple_tscn_text: str):
        tscn = parse_tscn(simple_tscn_text)
        serialized = tscn.to_tscn()
        reparsed = parse_tscn(serialized)
        assert len(reparsed.ext_resources) == len(tscn.ext_resources)
        assert reparsed.ext_resources[0].path == tscn.ext_resources[0].path

    def test_roundtrip_preserves_connections(self, simple_tscn_text: str):
        tscn = parse_tscn(simple_tscn_text)
        serialized = tscn.to_tscn()
        reparsed = parse_tscn(serialized)
        assert len(reparsed.connections) == len(tscn.connections)
        assert reparsed.connections[0].signal == tscn.connections[0].signal


class TestTscnToDict:
    def test_returns_nodes_list(self, simple_tscn_text: str):
        tscn = parse_tscn(simple_tscn_text)
        d = tscn_to_dict(tscn)
        assert "nodes" in d
        assert len(d["nodes"]) == 3

    def test_nodes_have_path(self, simple_tscn_text: str):
        tscn = parse_tscn(simple_tscn_text)
        d = tscn_to_dict(tscn)
        paths = [n["path"] for n in d["nodes"]]
        assert "Player" in paths
        assert "Player/Sprite2D" in paths

    def test_values_are_json_serializable(self, simple_tscn_text: str):
        import json
        tscn = parse_tscn(simple_tscn_text)
        d = tscn_to_dict(tscn)
        # Should not raise
        json.dumps(d)
