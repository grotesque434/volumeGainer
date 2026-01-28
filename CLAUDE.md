# Project guidelines (Python)

## Environment
- Use Python 3.11+
- Use venv: .venv
- Dependencies via pyproject.toml (preferred) or requirements.txt

## Code style
- Format: ruff format
- Lint: ruff check
- Typing: mypy (if configured)
- Prefer type hints for public functions
- Keep functions small and testable

## Testing
- Run: pytest -q
- When changing behavior, add or update tests
- Prefer unit tests; add integration tests only when needed

## Repo conventions
- Don’t edit generated files or lockfiles unless asked
- Keep changes minimal; avoid unrelated refactors
- Update docs/comments when behavior changes

## Commands
- Format: ruff format .
- Lint: ruff check .
- Tests: pytest -q
