# Verification Command Discovery

Do not use hardcoded project-specific command maps.

Discover verification commands from the current repository:

1. Detect ecosystem from files like `package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod`, `Makefile`, and CI configs.
2. Prefer explicit scripts/targets already defined by the project.
3. Run changed-file scopes where possible (lint/typecheck subset) before full-project checks.
4. If tests are placeholders or missing, add Tier 3 runtime evidence (import/load or focused smoke).
5. Record every baseline/after result in the ledger, including infeasible checks.

Common command patterns by ecosystem:
- Node: `npm run build`, `npm run typecheck`, `npm run lint -- <files>`, `npm test`
- Python: `pytest`, `ruff check <files>`, `mypy <files>`
- Rust: `cargo check`, `cargo test`, `cargo clippy -- -D warnings`
- Go: `go test ./...`, `go vet ./...`, `go build ./...`

Use discovered project commands over generic defaults when both exist.
