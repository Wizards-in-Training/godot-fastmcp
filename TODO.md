# TODO

Tracked ideas for future improvements. See the plan at
`.claude/plans/harmonic-growing-quill.md` for the full v1/v2 feature breakdown.

## Testing

- [ ] Convert tests to BDD style using `pytest-describe` (describe/context/it naming)
- [ ] Add type checking to CI — `mypy` or `pyright` (codebase already fully typed)
- [ ] Raise coverage threshold above 70% as untested paths are filled in
- [ ] Add tests for `script_*` and `resource_*` tools (currently no tool-level tests)
- [ ] Add parser tests for edge cases: multiline values, empty scenes, nested sub-resources

## Documentation

- [ ] Write README — setup instructions, env vars, Claude Desktop config snippet,
      tool reference
- [ ] Add `CHANGELOG.md` before first PyPI release
- [ ] Add `CONTRIBUTING.md` with dev setup steps

## Repo Hygiene

- [ ] Add `mypy`/`pyright` to pre-commit and CI
- [ ] Enable branch protection on `main` — require CI green before merge
- [ ] Add GitHub issue and PR templates (`.github/ISSUE_TEMPLATE/`, `.github/pull_request_template.md`)

## Publishing

- [ ] Set up PyPI trusted publishing via GitHub Actions OIDC (no API tokens needed)
- [ ] Adopt semantic versioning + release tags (`v0.1.0`); auto-publish on tag push
- [ ] Add `py.typed` marker is already present — confirm PEP 561 compliance

## v2 Features (deferred from MVP)

- [ ] **Editor integration** — connect to Godot's LSP (port 6005) for live diagnostics
      and autocompletion data without parsing files manually
- [ ] **Live scene manipulation** — EditorPlugin TCP bridge for real-time scene changes
      while the Godot editor is open
- [ ] **Headless execution** — `godot --headless --script` to run GDScript that needs
      engine evaluation (e.g. baking nav meshes, computing resource hashes)
- [ ] **Shader tools** — parse/validate `.gdshader` files
- [ ] **Animation tools** — read/write animation tracks embedded in scene files
- [ ] **Scene instancing** — full support for inherited scenes (scenes that extend
      other scenes via `[gd_scene ... load_steps=...]` with instanced root)
- [ ] **Signal connection management** — dedicated tools to add/remove/list connections
      beyond what the scene parser exposes
- [ ] **Richer class reference** — regenerate with `--dump-extension-api-with-docs`
      for method/property descriptions in `godot://class/{name}` responses
