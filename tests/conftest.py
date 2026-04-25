"""Shared pytest fixtures for godot-mcp tests."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES_DIR


@pytest.fixture
def simple_tscn_text() -> str:
    return (FIXTURES_DIR / "simple_scene.tscn").read_text(encoding="utf-8")


@pytest.fixture
def sample_tres_text() -> str:
    return (FIXTURES_DIR / "sample_resource.tres").read_text(encoding="utf-8")


@pytest.fixture
def project_godot_text() -> str:
    return (FIXTURES_DIR / "project.godot").read_text(encoding="utf-8")


@pytest.fixture
def fake_project(tmp_path: Path) -> Path:
    """Create a minimal fake Godot project in a temp directory."""
    shutil.copy(FIXTURES_DIR / "project.godot", tmp_path / "project.godot")

    scenes_dir = tmp_path / "scenes"
    scenes_dir.mkdir()
    shutil.copy(FIXTURES_DIR / "simple_scene.tscn", scenes_dir / "player.tscn")

    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    shutil.copy(FIXTURES_DIR / "sample_script.gd", scripts_dir / "player.gd")
    (scripts_dir / "game_manager.gd").write_text("extends Node\n", encoding="utf-8")
    (scripts_dir / "audio_manager.gd").write_text("extends Node\n", encoding="utf-8")

    res_dir = tmp_path / "resources"
    res_dir.mkdir()
    shutil.copy(FIXTURES_DIR / "sample_resource.tres", res_dir / "player_data.tres")

    return tmp_path
