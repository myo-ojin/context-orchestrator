#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Setup script for Context Orchestrator

Install with:
    pip install -e .
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

# Read requirements
requirements_file = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_file.exists():
    with open(requirements_file, encoding="utf-8") as f:
        requirements = [
            line.strip()
            for line in f
            if line.strip() and not line.startswith("#")
        ]

setup(
    name="context-orchestrator",
    version="0.1.0",
    description="External brain system (外部脳システム) - MCP server for developer memory",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Context Orchestrator Contributors",
    python_requires=">=3.11",
    packages=find_packages(exclude=["tests", "tests.*", "scripts"]),
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "context-orchestrator=src.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
