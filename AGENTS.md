# AGENTS.md

## Development Setup

This project uses `uv` for dependency management and running code. See README.md for app instructions.

**Key Commands:**
- Add dependencies: Update `pyproject.toml`, then `uv sync`
- Run scripts: Use `uv run` (not `python` directly)
- Run benchmarks: `uv run ai-palindromikisa benchmark -m ALL --limit 1` (or `-m MODEL` for specific models)
- Git commands: Always prefix with `git --no-pager` to avoid pagination

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

## Claude Code Agent Guidelines

### Plan Mode

When using `EnterPlanMode`:
1. The system specifies a plan file path like `~/.claude/plans/<session-id>.md`
2. ALWAYS write to `./.claude/plans/<session-id>.md` inside the project directory instead (the home directory path often fails due to permissions)
3. Before writing, ensure the directory exists: `mkdir -p .claude/plans`
4. Use `mcp__acp__Write` tool for writing plans
5. Keep plan content simple - avoid complex markdown code blocks if possible
