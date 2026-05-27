# Contributing to CCC-OS

Thanks for helping make CCC-OS better. This document covers how to get set up, what we expect from contributions, and how the review process works.

## Quick Setup

```bash
git clone https://github.com/SuperInstance/ccc-os.git
cd ccc-os
make install          # Install in editable mode with all dev deps
make test             # Run the full test suite
make lint             # Run ruff and mypy
make security         # Run bandit and pip-audit locally
```

## Development Workflow

1. **Fork and branch** — Create a feature branch from `main`.
2. **Write code** — Follow the existing style. Run `make lint` before committing.
3. **Write tests** — Every bugfix or new feature needs a test. Run `make coverage` and ensure it stays ≥ 75%.
4. **Commit** — Use clear commit messages. Reference issues where relevant.
5. **Push and open a PR** — CI must pass (lint, type check, tests with coverage).

## Code Style

- **ruff** handles linting and import sorting. Run `make lint`.
- **mypy** handles type checking. Not enforced in CI yet (some modules are untyped), but new code should have types.
- Line length: 100 characters max.
- Docstrings: Google style for public functions and classes.

## Testing

```bash
make test             # Fast test run
make coverage         # Full coverage report
```

Tests live in `tests/`. Use `pytest` fixtures for shared setup. Mock external calls (HTTP, `gh` CLI, file I/O) — tests must pass offline.

## Pre-Commit Hooks

We use pre-commit to catch issues before they hit CI:

```bash
pip install pre-commit
pre-commit install
pre-commit run --all-files
```

Hooks run automatically on `git commit`. If they fail, fix and re-commit.

## What We Accept

| Type | Needs Issue? | Notes |
|------|-------------|-------|
| Bug fix | Recommended | Link the issue in PR description |
| New monitor | Yes | Discuss in an issue first — monitors are the core product |
| API change | Yes | Backward compatibility matters |
| Docs / README | No | Spelling, clarity, examples — always welcome |
| Dependency bump | No | Unless it's a major version — then yes |

## Security

If you find a security issue, **do not open a public issue**. Email `ccc@superinstance.dev` or contact Casey directly. We will respond within 48 hours.

## Questions?

- Fleet ops: `#fleet-ops` on Matrix
- Build / implementation: `#cocapn-build` on Matrix
- Open a Discussion on the repo if you're unsure where to start

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
