# Agent Guidelines for EngFleet

## Commands

- **Install dependencies**: `uv sync`
- **Activate venv**: `source .venv/bin/activate`
- **Lint**: `uv run ruff check .`
- **Format**: `uv run ruff format .`
- **Run ADK web UI**: `cd agents && adk web`

## Code Style

- **Python version**: >=3.13
- **Imports**: Standard library → third-party → local (2 blank lines between sections)
- **Naming**: snake_case for functions/variables, PascalCase for classes, UPPER_CASE for constants
- **Types**: Use type hints, `from typing import TYPE_CHECKING` for circular imports
- **Error handling**: Use try/finally for cleanup, raise custom exceptions (ServerError, ValueError)
- **Logging**: Use `logging.getLogger(__name__)` with appropriate levels (DEBUG, INFO)
- **Async**: Use async/await patterns consistently
- **Docstrings**: Detailed for public functions, brief for private ones
- **Linting**: Ruff with extensive rules (see pyproject.toml for full config)

## Project Structure

- `agents/` - Contains the project ai agents
- `ref/` - Provides reference implementations of various agentic concepts
