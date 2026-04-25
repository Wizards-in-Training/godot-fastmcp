"""Tests for scene tools."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from godot_mcp.tools.scene import (
    scene_add_node,
    scene_create,
    scene_get_node,
    scene_read,
    scene_remove_node,
    scene_update_node,
)


@pytest.fixture(autouse=True)
def set_project_path(fake_project: Path):
    with patch.dict(os.environ, {"GODOT_PROJECT_PATH": str(fake_project)}):
        yield


class TestSceneRead:
    def test_reads_scene(self, fake_project: Path):
        result = scene_read("res://scenes/player.tscn")
        assert "nodes" in result
        assert len(result["nodes"]) == 3

    def test_returns_ext_resources(self, fake_project: Path):
        result = scene_read("res://scenes/player.tscn")
        assert len(result["ext_resources"]) == 1

    def test_returns_connections(self, fake_project: Path):
        result = scene_read("res://scenes/player.tscn")
        assert len(result["connections"]) == 1

    def test_raises_on_missing_file(self, fake_project: Path):
        with pytest.raises(FileNotFoundError):
            scene_read("res://scenes/nonexistent.tscn")

    def test_raises_on_wrong_extension(self, fake_project: Path):
        with pytest.raises(ValueError):
            scene_read("res://scripts/player.gd")


class TestSceneGetNode:
    def test_gets_root_node(self, fake_project: Path):
        node = scene_get_node("res://scenes/player.tscn", ".")
        assert node is not None
        assert node["name"] == "Player"

    def test_gets_child_node(self, fake_project: Path):
        node = scene_get_node("res://scenes/player.tscn", "Player/Sprite2D")
        assert node is not None
        assert node["type"] == "Sprite2D"

    def test_returns_none_for_missing(self, fake_project: Path):
        result = scene_get_node("res://scenes/player.tscn", "NonExistent")
        assert result is None


class TestSceneCreate:
    def test_creates_scene_file(self, fake_project: Path):
        result = scene_create("res://scenes/enemy.tscn", "Enemy", "CharacterBody2D")
        assert (fake_project / "scenes" / "enemy.tscn").exists()

    def test_returns_scene_structure(self, fake_project: Path):
        result = scene_create("res://scenes/ui.tscn", "UI", "Control")
        assert len(result["nodes"]) == 1
        assert result["nodes"][0]["name"] == "UI"
        assert result["nodes"][0]["type"] == "Control"

    def test_raises_if_already_exists(self, fake_project: Path):
        with pytest.raises(FileExistsError):
            scene_create("res://scenes/player.tscn", "Player")

    def test_raises_on_wrong_extension(self, fake_project: Path):
        with pytest.raises(ValueError):
            scene_create("res://scenes/test.gd", "Test")


class TestSceneAddNode:
    def test_adds_node(self, fake_project: Path):
        result = scene_add_node(
            "res://scenes/player.tscn",
            parent_path="Player",
            node_name="Label",
            node_type="Label",
        )
        nodes = [n["name"] for n in result["nodes"]]
        assert "Label" in nodes

    def test_node_has_correct_parent(self, fake_project: Path):
        scene_add_node(
            "res://scenes/player.tscn",
            parent_path="Player",
            node_name="HealthBar",
            node_type="ProgressBar",
        )
        result = scene_read("res://scenes/player.tscn")
        added = next((n for n in result["nodes"] if n["name"] == "HealthBar"), None)
        assert added is not None
        assert added["parent"] == "Player"

    def test_persists_to_disk(self, fake_project: Path):
        scene_add_node(
            "res://scenes/player.tscn",
            parent_path="Player",
            node_name="Camera2D",
            node_type="Camera2D",
        )
        # Re-read from disk
        result = scene_read("res://scenes/player.tscn")
        names = [n["name"] for n in result["nodes"]]
        assert "Camera2D" in names

    def test_raises_on_missing_parent(self, fake_project: Path):
        with pytest.raises(ValueError, match="Parent node not found"):
            scene_add_node(
                "res://scenes/player.tscn",
                parent_path="NonExistentParent",
                node_name="Child",
                node_type="Node",
            )


class TestSceneUpdateNode:
    def test_updates_property(self, fake_project: Path):
        scene_update_node(
            "res://scenes/player.tscn",
            node_path="Player/Sprite2D",
            properties={"position": "Vector2(100, 200)"},
        )
        result = scene_read("res://scenes/player.tscn")
        sprite = next(n for n in result["nodes"] if n["name"] == "Sprite2D")
        assert "Vector2(100, 200)" in sprite["properties"]["position"]

    def test_raises_on_missing_node(self, fake_project: Path):
        with pytest.raises(ValueError, match="Node not found"):
            scene_update_node(
                "res://scenes/player.tscn",
                node_path="NonExistent",
                properties={"visible": "true"},
            )


class TestSceneRemoveNode:
    def test_removes_node(self, fake_project: Path):
        scene_add_node(
            "res://scenes/player.tscn",
            parent_path="Player",
            node_name="ToRemove",
            node_type="Node",
        )
        result = scene_remove_node("res://scenes/player.tscn", "Player/ToRemove")
        names = [n["name"] for n in result["nodes"]]
        assert "ToRemove" not in names

    def test_raises_on_root_removal(self, fake_project: Path):
        with pytest.raises(ValueError, match="Cannot remove the root node"):
            scene_remove_node("res://scenes/player.tscn", ".")

    def test_raises_on_missing_node(self, fake_project: Path):
        with pytest.raises(ValueError, match="Node not found"):
            scene_remove_node("res://scenes/player.tscn", "NonExistent")
