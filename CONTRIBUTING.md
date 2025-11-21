# Contributing to Context Orchestrator

Thank you for your interest in contributing to Context Orchestrator! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Coding Guidelines](#coding-guidelines)
- [Testing](#testing)
- [Submitting Changes](#submitting-changes)
- [Issue Reporting](#issue-reporting)
- [Project Structure](#project-structure)

## Code of Conduct

### Our Pledge

We are committed to providing a welcoming and inclusive environment for all contributors. We expect:

- Respectful and constructive communication
- Focus on technical merit and project goals
- Acceptance of diverse perspectives and experiences
- Graceful handling of disagreements

### Unacceptable Behavior

- Harassment, discrimination, or personal attacks
- Trolling, insulting comments, or ad hominem attacks
- Publishing others' private information
- Any conduct that could be considered unprofessional

## Getting Started

### Prerequisites

Before contributing, ensure you have:

- **Python 3.11+** installed
- **Git** for version control
- **Ollama** running locally (for LLM integration)
- **Basic understanding** of MCP protocol (helpful but not required)

### Find an Issue

1. Check [GitHub Issues](https://github.com/myo-ojin/llm-brain/issues)
2. Look for issues tagged `good first issue` or `help wanted`
3. Comment on the issue to indicate you're working on it
4. Wait for maintainer acknowledgment before starting

### Fork and Clone

```bash
# Fork the repository on GitHub, then:
git clone https://github.com/YOUR_USERNAME/llm-brain.git
cd llm-brain

# Add upstream remote
git remote add upstream https://github.com/myo-ojin/llm-brain.git
```

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

## Issue Reporting

### Bug Reports

Use the bug report template:

```markdown
**Describe the bug**
A clear description of what the bug is.

**To Reproduce**
Steps to reproduce:
1. Run command '...'
2. Query with '...'
3. See error

**Expected behavior**
What you expected to happen.

**Actual behavior**
What actually happened.

**Environment**
- OS: Windows 11 / Ubuntu 22.04 / macOS 14
- Python version: 3.11.5
- Context Orchestrator version: 0.1.0
- Ollama version: 0.1.20

**Logs**
```
Paste relevant logs here
```

**Additional context**
Any other relevant information.
```

### Feature Requests

Use the feature request template:

```markdown
**Is your feature request related to a problem?**
A clear description of the problem.

**Describe the solution you'd like**
A clear description of what you want to happen.

**Describe alternatives you've considered**
Alternative solutions or features you've considered.

**Additional context**
Any other context or screenshots.

**Willingness to contribute**
- [ ] I'm willing to implement this feature
- [ ] I need help implementing this feature
- [ ] I'm just suggesting the idea
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

## Recognition

Contributors are recognized in:
- GitHub contributors page
- Release notes (for significant contributions)
- README acknowledgments (for major features)

## Questions?

- **GitHub Discussions**: Ask questions and discuss ideas
- **GitHub Issues**: Report bugs and request features
- **Documentation**: Check [CLAUDE.md](CLAUDE.md) for developer guide

Thank you for contributing to Context Orchestrator! 🙏
