# Contributing to Context Orchestrator

Thank you for your interest in contributing to Context Orchestrator! This document provides guidelines for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Coding Guidelines](#coding-guidelines)
- [Testing](#testing)
- [Submitting Changes](#submitting-changes)
- [Project Structure](#project-structure)

## Code of Conduct

Be respectful and constructive in all interactions. We aim to create a welcoming environment for all contributors.

## Getting Started

### Prerequisites

- Python 3.11 or higher
- Ollama (for local LLM integration)
- Git
- Basic understanding of:
  - MCP (Model Context Protocol)
  - Vector databases (Chroma)
  - LLM interactions

### First-Time Contributors

1. Fork the repository on GitHub
2. Clone your fork locally
3. Create a feature branch
4. Make your changes
5. Test your changes
6. Submit a pull request

## Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/llm-brain.git
cd llm-brain

# Add upstream remote
git remote add upstream https://github.com/myo-ojin/llm-brain.git

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install pytest pytest-cov black ruff mypy

# Install Ollama models
ollama pull nomic-embed-text
ollama pull qwen2.5:7b

# Run setup wizard
python scripts/setup.py
```

## Making Changes

### Branching Strategy

- `main`: Stable production-ready code
- `develop`: Integration branch for features
- `feature/*`: New features
- `fix/*`: Bug fixes
- `docs/*`: Documentation updates

### Creating a Branch

```bash
# Update your local repository
git fetch upstream
git checkout main
git merge upstream/main

# Create a feature branch
git checkout -b feature/your-feature-name
```

## Coding Guidelines

### Python Style

We follow **PEP 8** with some specific conventions:

- **Indentation**: 4 spaces (no tabs)
- **Line length**: 100 characters (soft limit), 120 (hard limit)
- **Encoding**: UTF-8 for all files (especially important for Japanese text)
- **Type hints**: Required for all function signatures

### Code Formatting

```bash
# Format code with Black
black .

# Check formatting
black --check .

# Lint with Ruff
ruff .

# Type check with MyPy
mypy src
```

### Naming Conventions

- **Functions**: `snake_case`
- **Classes**: `PascalCase`
- **Constants**: `UPPER_SNAKE_CASE`
- **Private methods**: `_leading_underscore`

### Example

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Module docstring

Brief description of the module.

Requirements: Requirement XX (reference requirement IDs)
"""

from typing import Optional, List
import logging

logger = logging.getLogger(__name__)


class MyClass:
    """
    Class docstring (Google style)

    Attributes:
        attribute_name: Description
    """

    def __init__(self, param: str):
        """Initialize MyClass

        Args:
            param: Parameter description
        """
        self.param = param

    def public_method(self, input_value: int) -> str:
        """
        Public method with type hints

        Args:
            input_value: Description of parameter

        Returns:
            Description of return value

        Raises:
            ValueError: Description of when this is raised
        """
        return str(input_value)

    def _private_method(self) -> None:
        """Private helper method"""
        pass
```

### Documentation

- **Docstrings**: Use Google style for all public APIs
- **Comments**: Explain "why", not "what"
- **Requirement IDs**: Reference requirements in comments (e.g., `# Req-03`)
- **File encoding**: Always use UTF-8, especially for files with Japanese text

### Japanese Text Handling

**CRITICAL**: Always save Japanese text files with UTF-8 encoding

```python
# Always specify UTF-8 when reading/writing files
with open('file.txt', 'r', encoding='utf-8') as f:
    content = f.read()

with open('file.txt', 'w', encoding='utf-8') as f:
    f.write('日本語テキスト')
```

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/unit/services/test_ingestion.py

# Run with coverage
pytest --cov=src --cov-report=html

# Run integration tests
pytest tests/integration/
```

### Writing Tests

```python
import pytest
from unittest.mock import Mock, patch

def test_example_function():
    """Test example function with descriptive name"""
    # Arrange
    input_data = "test"
    expected = "TEST"

    # Act
    result = example_function(input_data)

    # Assert
    assert result == expected

def test_error_handling():
    """Test error handling"""
    with pytest.raises(ValueError):
        example_function(None)
```

### Test Coverage Goals

- **Unit tests**: ≥85% statement coverage
- **Integration tests**: Cover main workflows
- **Error handling**: Test all exception paths

## Submitting Changes

### Before Submitting

1. **Format code**: `black .`
2. **Lint**: `ruff .`
3. **Type check**: `mypy src` (optional, best effort)
4. **Run tests**: `pytest`
5. **Update documentation**: If adding features
6. **Test manually**: Verify your changes work

### Commit Message Format

Use Conventional Commits format:

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Code style (formatting, no logic change)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples**:

```
feat(cli): add export command for memory backup

Implemented JSON export functionality with:
- Full memory export including embeddings
- File size reporting
- Error handling for missing database

Requirements: Requirement 13
```

```
fix(parser): handle empty Wikilinks correctly

Fixed bug where empty Wikilinks [[]] caused parser to crash.
Now properly skips empty links during extraction.

Fixes #123
```

### Pull Request Process

1. **Push your branch**: `git push origin feature/your-feature`
2. **Create PR** on GitHub
3. **Fill PR template**:
   - Description of changes
   - Related issues
   - Testing performed
   - Screenshots (if UI changes)
4. **Wait for review**
5. **Address feedback**
6. **Merge** after approval

### PR Template

```markdown
## Description
Brief description of your changes

## Related Issues
Fixes #123

## Changes Made
- Change 1
- Change 2

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests pass
- [ ] Manual testing performed

## Checklist
- [ ] Code formatted with Black
- [ ] Linting passes (Ruff)
- [ ] Tests pass
- [ ] Documentation updated
- [ ] Commit messages follow convention
```

## Project Structure

```
llm-brain/
├── src/
│   ├── main.py                 # Entry point
│   ├── config.py               # Configuration management
│   ├── cli.py                  # CLI commands
│   ├── mcp/                    # MCP protocol handler
│   ├── services/               # Core services
│   │   ├── ingestion.py
│   │   ├── search.py
│   │   ├── consolidation.py
│   │   ├── session_manager.py
│   │   ├── obsidian_parser.py
│   │   └── obsidian_watcher.py
│   ├── models/                 # Model routing and LLM clients
│   ├── processing/             # Chunking, classification, indexing
│   ├── storage/                # Vector DB and BM25 index
│   └── utils/                  # Logging and errors
├── tests/
│   ├── unit/                   # Unit tests
│   └── integration/            # Integration tests
├── scripts/                    # Setup and utility scripts
├── .kiro/specs/               # Project specifications
├── CLAUDE.md                   # Developer guide
├── README.md                   # User documentation
└── CONTRIBUTING.md             # This file
```

## Areas for Contribution

### High Priority

- **Testing**: Add unit tests for untested components
- **Documentation**: Improve examples and tutorials
- **Integration**: Additional vault integrations (Notion, etc.)
- **Performance**: Optimize search and indexing

### Good First Issues

Look for issues labeled:
- `good-first-issue`
- `documentation`
- `help-wanted`

### Feature Ideas

- Web UI for memory exploration
- Additional LLM integrations (GPT-4, etc.)
- Export formats (Markdown, CSV)
- Advanced search filters
- Memory analytics dashboard

## Questions?

- **Documentation**: See [CLAUDE.md](CLAUDE.md)
- **Issues**: [GitHub Issues](https://github.com/myo-ojin/llm-brain/issues)
- **Discussions**: [GitHub Discussions](https://github.com/myo-ojin/llm-brain/discussions)

Thank you for contributing to Context Orchestrator! 🎉
