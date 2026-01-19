# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

The `variables` tool helps store sensitive and non-sensitive variables next to code in a standardized YAML format. Variables can be encrypted using different backends (age encryption, dummy), exported to various formats (Kubernetes ConfigMap/Secret, bash env), or injected as environment variables for command execution.

**Important**: This is a SourceHut project. The GitHub repo is read-only. Track issues at https://todo.sr.ht/~radium226/variables

## Development Commands

### Code Quality & Testing
```bash
# Run all checks (linting, type hints, tests)
mise run check-code

# Individual checks
uv run ruff check ./src
uv run ruff check ./tests
uv run mypy ./src
uv run mypy ./tests
uv run pytest ./tests

# Run single test
uv run pytest tests/test_variables.py::test_encrypt_and_decrypt
uv run pytest tests/test_backends.py::test_backend
```

### Ticket Management
```bash
# Open new ticket (creates branch: ticket-{id}-{slug})
mise run open-ticket "Ticket title here"

# Close ticket (squash merge current branch to main, resolve ticket)
mise run close-ticket
```

## Architecture

### Plugin-Based Backend System

The project uses a **Service Provider Interface (SPI)** pattern for encryption backends via Python entry points. Backends are discovered dynamically at runtime.

**Entry Point Registration** (pyproject.toml:66):
```toml
[project.entry-points."radium226.variables.backend"]
dummy = "radium226.variables.backends.dummy"
age = "radium226.variables.backends.age"
```

**Backend Discovery** (spi.py:54):
- `list_factories()` discovers backends via `entry_points(group="radium226.variables.backend")`
- Each backend module must export: `parse_config(dict[str, str]) -> Config` and `create_backend(Config) -> ContextManager[Backend]`
- The `Backend` protocol requires: `encrypt_value(bytes) -> bytes` and `decrypt_value(bytes) -> bytes`

**Adding New Backends**:
1. Create module in `src/radium226/variables/backends/`
2. Implement `parse_config` and `create_backend` functions
3. Backend class must implement `encrypt_value()` and `decrypt_value()`
4. Register in pyproject.toml entry points

### Variable Processing Pipeline

**Storage Format** (variables.py:29):
- Encrypted values prefixed with `"encrypted:"` followed by base64-encoded ciphertext
- Variables stored as YAML with fields: `name`, `value`, `visibility` (plain/secret), `type` (text/file)

**Command Execution Flow** (variables.py:213):
1. Load variables from YAML file(s)
2. Decrypt variables marked as `visibility: secret`
3. For `type: file` variables, write value to temp file and set env var to file path
4. Interpolate command arguments using Jinja2 templates (variables in `{{ }}`)
5. Variables used in interpolation removed from environment, others passed as env vars
6. Execute command with combined environment

**Example**: `variables exec -v secrets.yaml -- cat {{ CONFIG_FILE }}`
- If `CONFIG_FILE` is type=file, creates temp file with content, interpolates path into command
- If `API_KEY` exists but not used in command, passed as environment variable

### Click CLI Architecture

**Context Management** (app.py:50-63):
- Root `@group()` command initializes backend in `context.obj.backend`
- Backend created using `context.with_resource()` for proper lifecycle management
- Subcommands receive backend via `@pass_context`

**Commands**:
- `encrypt <file>`: Encrypt all secret variables in file
- `decrypt <file>`: Decrypt all encrypted variables in file
- `exec -v <files> -- <command>`: Execute command with decrypted variables
- `export -t <target> <file>`: Export to kubectl manifests (`kubectl`) or bash env (`bash`)
- `set -v <file> <name> <value>`: Set/update variable (auto-encrypts if visibility=secret)

### Type System

**Python 3.11+ Compatibility**:
- Use `TypeAlias` from `typing` module (not `type` keyword from 3.13+)
- Generic classes use `Generic[T]` with separate `TypeVar` declaration
- Union types can use `|` syntax (available since 3.10)

**Strict Type Checking** (pyproject.toml:35):
- mypy configured with strict settings: `disallow_untyped_defs=true`, `warn_return_any=true`
- All functions must have type annotations
- Use `@overload` for functions with multiple signatures (see variables.py:33-39)

### Test Structure

**Parametrized Backend Testing** (test_backends.py:36):
- Backends tested via pytest parametrization with indirect fixtures
- Add new backends to `@pytest.mark.parametrize` list
- All backends must pass encryption round-trip test

**Running Individual Tests**:
```bash
# Specific backend
uv run pytest tests/test_backends.py::test_backend[age-keypair]

# All tests for a file
uv run pytest tests/test_variables.py -v
```

## Python Version

Requires Python >= 3.11. Uses modern type hints (TypeAlias, Generic[T], union syntax with `|`).
