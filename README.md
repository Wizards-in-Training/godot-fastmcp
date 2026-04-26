# godot-mcp

An MCP server for Godot 4 game engine projects. Enables AI assistants (Claude, etc.) to read, create, and modify Godot projects via direct file manipulation — no running Godot instance required.

## Features

- **Scene tools** — read, create, add/update/remove nodes in `.tscn` files
- **Script tools** — read, write, validate, and format `.gd` files via gdtoolkit
- **Resource tools** — read and create `.tres` files
- **Project tools** — inspect `project.godot`, list scenes/scripts/resources, file tree
- **Class reference** — look up Godot built-in class properties, methods, and signals
- **MCP resources** — `godot://project/settings`, `godot://scene/{path}`, `godot://class/{name}`

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- Godot 4 (for class reference features — optional, see below)

## Setup

```bash
# Install dependencies
uv sync --all-extras --dev

# Install pre-commit hooks (contributors)
uv run pre-commit install
```

No manual classdata generation needed — see [Class Reference Data](#class-reference-data) below.

## Configuration

Set the `GODOT_PROJECT_PATH` environment variable to the root of your Godot 4 project (the directory containing `project.godot`).

## Claude Desktop Integration

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "godot": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/godot-fastmcp", "godot-mcp"],
      "env": {
        "GODOT_PROJECT_PATH": "/path/to/your/godot/project"
      }
    }
  }
}
```

## Claude Code Integration

Add to `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "godot": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/godot-fastmcp", "godot-mcp"],
      "env": {
        "GODOT_PROJECT_PATH": "/path/to/your/godot/project"
      }
    }
  }
}
```

## Tools

### Project

| Tool | Description |
|------|-------------|
| `project_info` | Project name, Godot version, main scene, autoloads |
| `project_list_scenes` | All `.tscn` files in the project |
| `project_list_scripts` | All `.gd` files in the project |
| `project_list_resources` | All `.tres` files in the project |
| `project_file_tree` | Directory tree (respects `.gdignore`) |

### Scene

| Tool | Description |
|------|-------------|
| `scene_read` | Parse a `.tscn` file — nodes, resources, connections |
| `scene_get_node` | Get a specific node by path |
| `scene_create` | Create a new scene with a root node |
| `scene_add_node` | Add a node under a given parent |
| `scene_update_node` | Update node properties |
| `scene_remove_node` | Remove a node and its children |

### Script

| Tool | Description |
|------|-------------|
| `script_read` | Read a `.gd` file |
| `script_write` | Write/overwrite a `.gd` file |
| `script_create` | Create a new script with a class template |
| `script_validate` | Lint with gdtoolkit, return diagnostics |
| `script_format` | Format with gdtoolkit |

### Resource

| Tool | Description |
|------|-------------|
| `resource_read` | Parse a `.tres` file |
| `resource_create` | Create a new `.tres` file |

### Class Reference

| Tool | Description |
|------|-------------|
| `classdata_status` | Check whether class reference data is available for the current project |
| `classdata_generate` | Generate class reference data from the local Godot installation |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GODOT_PROJECT_PATH` | Yes | Path to your Godot 4 project root |
| `GODOT_EXECUTABLE` | No | Path to Godot binary (overrides auto-discovery for `classdata_generate`) |

## Development

```bash
# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=godot_mcp --cov-report=term-missing

# Lint and format
uv run ruff check .
uv run ruff format .

# Run all pre-commit checks
uv run pre-commit run --all-files
```

## Class Reference Data

The `godot://class/{name}` resource and `classdata_*` tools require an `extension_api.json` snapshot generated from your local Godot installation. This file is gitignored and generated on demand — **no manual setup step required**.

### How it works

1. On the first class lookup, the server reads the target Godot version from `project.godot` (the `config/features` field, e.g. `"4.3"`).
2. It checks for a cached file matching that version (e.g. `extension_api_4_3.json`).
3. If the file is missing, it searches common Godot install locations and generates it automatically.
4. Each major.minor version gets its own cache file, so switching between projects that target different Godot versions works without any manual steps.

### When auto-discovery fails

If Godot isn't installed in a standard location, ask the AI assistant to check the status and generate the data:

> "Check classdata status and generate it if needed"

The assistant will call `classdata_status` to diagnose the situation and `classdata_generate` to produce the data, prompting you for the Godot path if it can't find it automatically.

You can also set `GODOT_EXECUTABLE` in the MCP server config to skip auto-discovery:

```json
"env": {
  "GODOT_PROJECT_PATH": "/path/to/project",
  "GODOT_EXECUTABLE": "/path/to/Godot.app/Contents/MacOS/Godot"
}
```

## License

MIT
