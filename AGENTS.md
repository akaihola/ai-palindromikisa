# AGENTS.md

## Development Setup

This project uses `uv` as the package manager and dependency resolver. You must use `uv` commands to manage dependencies and run the project.

### Installing Dependencies

To install all dependencies, run:
```bash
uv sync
```

### Adding New Dependencies

When adding new dependencies (like `llm-gemini`), update `pyproject.toml` and then run:
```bash
uv sync
```

### Running the Project

Use `uv` to run commands:
```bash
uv run python -m ai_palindromikisa.benchmark -m gemini/gemini-2.0-flash
```

or use the script entry point:
```bash
uv run benchmark -m gemini/gemini-2.0-flash
```

### Important Notes

- Do NOT use `pip install` directly - always use `uv sync`
- Do NOT use `python` directly for running scripts - use `uv run`
- The project relies on `uv` for proper dependency management and virtual environment handling

## Code Style Guidelines

### File Operations

- Always use `pathlib.Path` instead of the built-in `open()` function for file operations
- Use `Path.read_text()` and `Path.write_text()` for simple read/write operations
- Use `Path` objects for path manipulation and directory operations

Example:
```python
from pathlib import Path

# Instead of: with open("file.txt", "r") as f: content = f.read()
content = Path("file.txt").read_text()

# Instead of: with open("file.txt", "w") as f: f.write(content)
Path("file.txt").write_text(content)
```