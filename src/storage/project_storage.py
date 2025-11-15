#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Project Storage

Provides persistent storage for Project metadata using JSON.
Inspired by NotebookLM's library management approach.

Requirements: Phase 15 - Project Management
"""

from typing import List, Optional, Dict, Any
from pathlib import Path
import json
import logging
from datetime import datetime

from src.models import Project

logger = logging.getLogger(__name__)


class ProjectStorage:
    """
    Project storage with JSON persistence

    Manages project metadata storage in a human-readable JSON file.
    Projects are stored in-memory and persisted to disk after each modification.

    Attributes:
        persist_path: Path to JSON file for persistence
        projects: Dict mapping project_id to Project instance
    """

    def __init__(self, persist_path: str):
        """
        Initialize project storage

        Args:
            persist_path: Path to JSON file (e.g., ~/.context-orchestrator/projects.json)
        """
        self.persist_path = Path(persist_path)
        self.persist_path.parent.mkdir(parents=True, exist_ok=True)

        # In-memory storage
        self.projects: Dict[str, Project] = {}

        # Load existing projects if available
        self._load()

        logger.info(f"Initialized ProjectStorage at {self.persist_path}")
        logger.info(f"Loaded {len(self.projects)} projects")

    def save_project(self, project: Project) -> None:
        """
        Save a project to storage

        Args:
            project: Project instance to save

        Note:
            If project with same ID exists, it will be replaced.
            Updates the project's updated_at timestamp.
        """
        if project.id in self.projects:
            logger.debug(f"Project {project.id} already exists, updating")

        # Update timestamp
        project.updated_at = datetime.now()

        self.projects[project.id] = project
        self._save()

        logger.debug(f"Saved project: {project.id} ({project.name})")

    def load_project(self, project_id: str) -> Optional[Project]:
        """
        Load a project by ID

        Args:
            project_id: Unique project ID

        Returns:
            Project instance, or None if not found
        """
        project = self.projects.get(project_id)

        if project:
            logger.debug(f"Loaded project: {project_id}")
        else:
            logger.debug(f"Project not found: {project_id}")

        return project

    def list_projects(self) -> List[Project]:
        """
        List all projects

        Returns:
            List of all Project instances, sorted by last_accessed (descending)
        """
        projects = list(self.projects.values())

        # Sort by last_accessed (most recent first)
        projects.sort(key=lambda p: p.last_accessed, reverse=True)

        logger.debug(f"Listed {len(projects)} projects")
        return projects

    def delete_project(self, project_id: str) -> bool:
        """
        Delete a project from storage

        Args:
            project_id: Unique project ID

        Returns:
            True if project was deleted, False if not found
        """
        if project_id not in self.projects:
            logger.warning(f"Project not found for deletion: {project_id}")
            return False

        project_name = self.projects[project_id].name
        del self.projects[project_id]
        self._save()

        logger.info(f"Deleted project: {project_id} ({project_name})")
        return True

    def update_project(self, project: Project) -> None:
        """
        Update an existing project

        Args:
            project: Project instance with updated fields

        Note:
            Equivalent to save_project(). Provided for API clarity.
        """
        if project.id not in self.projects:
            logger.warning(f"Project {project.id} not found, creating new entry")

        self.save_project(project)

    def find_by_name(self, name: str) -> Optional[Project]:
        """
        Find project by name (case-insensitive)

        Args:
            name: Project name to search

        Returns:
            First matching Project, or None if not found
        """
        name_lower = name.lower()

        for project in self.projects.values():
            if project.name.lower() == name_lower:
                logger.debug(f"Found project by name: {name} -> {project.id}")
                return project

        logger.debug(f"No project found with name: {name}")
        return None

    def find_by_tags(self, tags: List[str]) -> List[Project]:
        """
        Find projects containing all specified tags

        Args:
            tags: List of tags to match (AND logic)

        Returns:
            List of matching Projects, sorted by last_accessed
        """
        tags_lower = [tag.lower() for tag in tags]
        matches = []

        for project in self.projects.values():
            project_tags_lower = [tag.lower() for tag in project.tags]

            # Check if all specified tags are present
            if all(tag in project_tags_lower for tag in tags_lower):
                matches.append(project)

        # Sort by last_accessed (most recent first)
        matches.sort(key=lambda p: p.last_accessed, reverse=True)

        logger.debug(f"Found {len(matches)} projects with tags: {tags}")
        return matches

    def update_access_time(self, project_id: str) -> None:
        """
        Update last_accessed timestamp for a project

        Args:
            project_id: Unique project ID

        Note:
            Called when project is searched or accessed.
            Used for recency-based sorting.
        """
        project = self.projects.get(project_id)

        if not project:
            logger.warning(f"Cannot update access time: project {project_id} not found")
            return

        project.last_accessed = datetime.now()
        self._save()

        logger.debug(f"Updated access time for project: {project_id}")

    def increment_memory_count(self, project_id: str) -> None:
        """
        Increment memory count for a project

        Args:
            project_id: Unique project ID

        Note:
            Called when a memory is associated with this project.
        """
        project = self.projects.get(project_id)

        if not project:
            logger.warning(f"Cannot increment memory count: project {project_id} not found")
            return

        project.memory_count += 1
        project.updated_at = datetime.now()
        self._save()

        logger.debug(f"Incremented memory count for project {project_id}: {project.memory_count}")

    def decrement_memory_count(self, project_id: str) -> None:
        """
        Decrement memory count for a project

        Args:
            project_id: Unique project ID

        Note:
            Called when a memory is removed from this project.
            Count will not go below 0.
        """
        project = self.projects.get(project_id)

        if not project:
            logger.warning(f"Cannot decrement memory count: project {project_id} not found")
            return

        project.memory_count = max(0, project.memory_count - 1)
        project.updated_at = datetime.now()
        self._save()

        logger.debug(f"Decremented memory count for project {project_id}: {project.memory_count}")

    def count(self) -> int:
        """
        Get total number of projects

        Returns:
            Number of projects in storage
        """
        return len(self.projects)

    def _save(self) -> None:
        """
        Save projects to disk (JSON format)

        Saves all projects as a JSON array with human-readable formatting.
        """
        try:
            # Convert all projects to dict format
            data = {
                'projects': [
                    project.to_dict() for project in self.projects.values()
                ],
                'version': '1.0',  # For future schema migrations
                'last_updated': datetime.now().isoformat()
            }

            # Write to file with pretty formatting
            with open(self.persist_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            logger.debug(f"Saved {len(self.projects)} projects to {self.persist_path}")

        except Exception as e:
            logger.error(f"Failed to save projects: {e}")
            # Don't raise - continue operation even if save fails

    def _load(self) -> None:
        """
        Load projects from disk

        If file doesn't exist or is corrupted, starts with empty storage.
        """
        if not self.persist_path.exists():
            logger.debug("No existing projects file found, starting fresh")
            return

        try:
            with open(self.persist_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Load projects from array
            projects_data = data.get('projects', [])

            for project_dict in projects_data:
                project = Project.from_dict(project_dict)
                self.projects[project.id] = project

            logger.info(f"Loaded {len(self.projects)} projects from disk")

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse projects JSON: {e}")
            logger.warning("Starting with empty storage")
            self.projects = {}

        except Exception as e:
            logger.error(f"Failed to load projects: {e}")
            logger.warning("Starting with empty storage")
            self.projects = {}
