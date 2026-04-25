"""Tests for project inspection tools."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from godot_mcp.tools.project import (
    project_file_tree,
    project_info,
    project_list_resources,
    project_list_scenes,
    project_list_scripts,
)


@pytest.fixture(autouse=True)
def set_project_path(fake_project: Path):
    """Set GODOT_PROJECT_PATH for all tests in this module."""
    with patch.dict(os.environ, {"GODOT_PROJECT_PATH": str(fake_project)}):
        # Clear the cached project root if any
        yield


class TestProjectInfo:
    def test_returns_project_name(self, fake_project: Path):
        info = project_info()
        assert info["name"] == "My Test Game"

    def test_returns_main_scene(self, fake_project: Path):
        info = project_info()
        assert info["main_scene"] == "res://scenes/main.tscn"

    def test_returns_autoloads(self, fake_project: Path):
        info = project_info()
        assert "GameManager" in info["autoloads"]

    def test_returns_project_root(self, fake_project: Path):
        info = project_info()
        assert info["project_root"] == str(fake_project)


class TestProjectListScenes:
    def test_finds_tscn_files(self, fake_project: Path):
        scenes = project_list_scenes()
        assert any("player.tscn" in s for s in scenes)

    def test_returns_res_paths(self, fake_project: Path):
        scenes = project_list_scenes()
        assert all(s.startswith("res://") for s in scenes)


class TestProjectListScripts:
    def test_finds_gd_files(self, fake_project: Path):
        scripts = project_list_scripts()
        assert any("player.gd" in s for s in scripts)

    def test_returns_res_paths(self, fake_project: Path):
        scripts = project_list_scripts()
        assert all(s.startswith("res://") for s in scripts)


class TestProjectListResources:
    def test_finds_tres_files(self, fake_project: Path):
        resources = project_list_resources()
        assert any("player_data.tres" in r for r in resources)

    def test_returns_res_paths(self, fake_project: Path):
        resources = project_list_resources()
        assert all(r.startswith("res://") for r in resources)


class TestProjectFileTree:
    def test_returns_dict(self, fake_project: Path):
        tree = project_file_tree()
        assert isinstance(tree, dict)

    def test_contains_directories(self, fake_project: Path):
        tree = project_file_tree()
        assert any(k.endswith("/") for k in tree)

    def test_contains_project_godot(self, fake_project: Path):
        tree = project_file_tree()
        assert "project.godot" in tree

    def test_respects_max_depth(self, fake_project: Path):
        tree = project_file_tree(max_depth=1)
        # With depth=1, directories should show _truncated
        for key, val in tree.items():
            if key.endswith("/"):
                assert val == {"_truncated": True}
