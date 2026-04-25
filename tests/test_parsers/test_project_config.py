"""Tests for project.godot parser."""

from __future__ import annotations

from godot_mcp.parsers.project_config import (
    get_autoloads,
    get_main_scene,
    get_project_name,
    parse_project_config_text,
)


class TestParseProjectConfig:
    def test_parses_project_name(self, project_godot_text: str):
        config = parse_project_config_text(project_godot_text)
        assert get_project_name(config) == "My Test Game"

    def test_parses_main_scene(self, project_godot_text: str):
        config = parse_project_config_text(project_godot_text)
        assert get_main_scene(config) == "res://scenes/main.tscn"

    def test_parses_autoloads(self, project_godot_text: str):
        config = parse_project_config_text(project_godot_text)
        autoloads = get_autoloads(config)
        assert "GameManager" in autoloads
        assert autoloads["GameManager"] == "res://scripts/game_manager.gd"
        assert "AudioManager" in autoloads

    def test_autoload_strips_star(self, project_godot_text: str):
        config = parse_project_config_text(project_godot_text)
        autoloads = get_autoloads(config)
        # Values should not start with *
        for path in autoloads.values():
            assert not path.startswith("*")

    def test_parses_sections(self, project_godot_text: str):
        config = parse_project_config_text(project_godot_text)
        assert "application" in config
        assert "autoload" in config
        assert "rendering" in config

    def test_packed_string_array_features(self, project_godot_text: str):
        config = parse_project_config_text(project_godot_text)
        features = config["application"].get("config/features")
        # Should be parsed as a PackedArray or list
        assert features is not None
