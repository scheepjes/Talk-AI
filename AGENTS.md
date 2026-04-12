# AGENTS.md - AI Coding Assistant Guidelines

## Project Overview
Python script (`talk.py`) for conversational AI interaction between two llama.cpp servers. Uses colorama for colored output.

## Build/Lint/Test Commands
- **Run script**: `python talk.py`
- **Check syntax**: `python -m py_compile talk.py`
- **Lint**: `flake8 talk.py` or `pylint talk.py`
- **Type check**: `mypy talk.py`
- **Format**: `black talk.py` or `ruff format talk.py`
- **Test single test**: `pytest tests/test_name.py -v` (if tests exist)

*Note: This project lacks formal test infrastructure. Manual testing via CLI execution.*

## Code Style Guidelines

### Imports
- Standard library imports first (e.g., `import json`, `import time`)
- Third-party imports next (e.g., `from colorama import init, Fore, Style`)
- Blank line between import groups
- Use explicit imports when possible

### Formatting
- 4-space indentation
- Maximum line length: 100 characters
- Blank lines between functions and logical sections
- Use f-strings for string interpolation
- One expression per line for readability

### Type Hints
- Use type hints for function parameters and return values
- Example: `def send_message(server_url: str, messages: list, max_tokens: int = 256) -> str:`

### Naming Conventions
- **Functions**: snake_case (e.g., `send_message`, `truncate_history`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `SERVER_A_URL`, `DEPTH_TEMPLATES`)
- **Variables**: snake_case (e.g., `system_instruction`, `turn_count`)
- **Classes**: PascalCase (if any)

### Error Handling
- Use specific exception types (e.g., `requests.exceptions.ConnectionError`)
- Wrap network operations in try-except blocks
- Return user-friendly error messages
- Use `finally` blocks for cleanup/logging

### Documentation
- Docstrings for all functions explaining purpose and parameters
- Inline comments for complex logic or non-obvious decisions
- Keep comments concise and actionable

### Code Organization
- Configuration constants at top of file with clear separation
- Functions should have single responsibility
- Keep functions under 50 lines when possible
- Use helper functions for repeated logic (e.g., `truncate_history`)

## Cursor/Copilot Rules
*No existing Cursor or Copilot rules found in repository.*

## Additional Notes
- Uses colorama library for terminal output colors
- Implements conversation history management with truncation
- Includes safety limits (max 20 turns) to prevent infinite loops
- Handles KeyboardInterrupt gracefully for clean exit