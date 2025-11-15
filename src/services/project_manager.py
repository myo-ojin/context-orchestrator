#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Project Manager Service

Handles project management operations:
- Create, read, update, delete projects
- Auto-select projects based on query context
- Manage project-memory associations
- Track project usage statistics

Inspired by NotebookLM's library management approach.

Requirements: Phase 15 - Project Management
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
import uuid

from src.models import Project, ModelRouter
from src.storage.project_storage import ProjectStorage

logger = logging.getLogger(__name__)


class ProjectManager:
    """
    Service for managing projects and project-memory associations

    Projects provide a way to organize memories by topic, codebase, or context.
    This enables scoped searches and better memory organization.

    Attributes:
        project_storage: ProjectStorage instance for persistence
        model_router: ModelRouter for LLM-based auto-selection
    """

    def __init__(
        self,
        project_storage: ProjectStorage,
        model_router: ModelRouter
    ):
        """
        Initialize Project Manager

        Args:
            project_storage: ProjectStorage instance
            model_router: ModelRouter instance for LLM tasks
        """
        self.project_storage = project_storage
        self.model_router = model_router

        logger.info("Initialized ProjectManager")

    def create_project(
        self,
        name: str,
        description: str,
        tags: Optional[List[str]] = None
    ) -> Project:
        """
        Create a new project

        Args:
            name: Project name (e.g., "my-react-app")
            description: Project description
            tags: Optional list of tags (e.g., ["react", "typescript"])

        Returns:
            Created Project instance

        Raises:
            ValueError: If project with same name already exists

        Example:
            >>> manager = ProjectManager(...)
            >>> project = manager.create_project(
            ...     name="my-react-app",
            ...     description="React + TypeScript project",
            ...     tags=["react", "typescript", "frontend"]
            ... )
            >>> print(project.id)
        """
        # Check if project with same name exists
        existing = self.project_storage.find_by_name(name)
        if existing:
            raise ValueError(f"Project with name '{name}' already exists (ID: {existing.id})")

        # Create new project
        project = Project(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            tags=tags or [],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            memory_count=0,
            last_accessed=datetime.now(),
            metadata={}
        )

        # Save to storage
        self.project_storage.save_project(project)

        logger.info(f"Created project: {project.id} ({project.name})")
        return project

    def get_project(self, project_id: str) -> Optional[Project]:
        """
        Get project by ID

        Args:
            project_id: Unique project ID

        Returns:
            Project instance, or None if not found
        """
        project = self.project_storage.load_project(project_id)

        if project:
            # Update access time
            self.project_storage.update_access_time(project_id)

        return project

    def get_project_by_name(self, name: str) -> Optional[Project]:
        """
        Get project by name (case-insensitive)

        Args:
            name: Project name

        Returns:
            Project instance, or None if not found
        """
        project = self.project_storage.find_by_name(name)

        if project:
            # Update access time
            self.project_storage.update_access_time(project.id)

        return project

    def list_projects(self) -> List[Project]:
        """
        List all projects

        Returns:
            List of all projects, sorted by last_accessed (descending)
        """
        return self.project_storage.list_projects()

    def update_project(
        self,
        project_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Project]:
        """
        Update project fields

        Args:
            project_id: Project ID to update
            name: New name (optional)
            description: New description (optional)
            tags: New tags (optional)
            metadata: New metadata (optional)

        Returns:
            Updated Project instance, or None if not found

        Note:
            Only provided fields will be updated. None values are ignored.
        """
        project = self.project_storage.load_project(project_id)

        if not project:
            logger.warning(f"Cannot update: project {project_id} not found")
            return None

        # Update fields
        if name is not None:
            project.name = name

        if description is not None:
            project.description = description

        if tags is not None:
            project.tags = tags

        if metadata is not None:
            project.metadata.update(metadata)

        # Save updated project
        self.project_storage.update_project(project)

        logger.info(f"Updated project: {project_id}")
        return project

    def delete_project(self, project_id: str) -> bool:
        """
        Delete a project

        Args:
            project_id: Project ID to delete

        Returns:
            True if deleted, False if not found

        Note:
            This does NOT delete associated memories, only removes
            the project_id reference from them.
        """
        success = self.project_storage.delete_project(project_id)

        if success:
            logger.info(f"Deleted project: {project_id}")
        else:
            logger.warning(f"Cannot delete: project {project_id} not found")

        return success

    def find_projects_by_tags(self, tags: List[str]) -> List[Project]:
        """
        Find projects containing all specified tags

        Args:
            tags: List of tags to match (AND logic)

        Returns:
            List of matching projects, sorted by last_accessed

        Example:
            >>> projects = manager.find_projects_by_tags(["react", "typescript"])
            >>> for project in projects:
            ...     print(project.name)
        """
        return self.project_storage.find_by_tags(tags)

    def auto_select_project(self, query: str) -> Optional[str]:
        """
        Automatically select most relevant project based on query

        Args:
            query: User query or conversation content

        Returns:
            Project ID if match found, None otherwise

        Implementation:
            Uses LLM to analyze query and match against project descriptions/tags.
            Returns the most relevant project, or None if no good match.

        Example:
            >>> query = "React hooks error handling"
            >>> project_id = manager.auto_select_project(query)
            >>> if project_id:
            ...     print(f"Selected project: {project_id}")
        """
        projects = self.project_storage.list_projects()

        if not projects:
            logger.debug("No projects available for auto-selection")
            return None

        # Build context for LLM
        project_context = self._build_project_context(projects)

        # Generate prompt for LLM
        prompt = self._build_selection_prompt(query, project_context)

        try:
            # Use local LLM for fast inference
            response = self.model_router.route_task(
                task_type='short_summary',  # Fast local inference
                prompt=prompt,
                max_tokens=50
            )

            # Parse response to extract project ID
            project_id = self._parse_selection_response(response, projects)

            if project_id:
                logger.info(f"Auto-selected project: {project_id}")
                # Update access time
                self.project_storage.update_access_time(project_id)
            else:
                logger.debug("No suitable project found for query")

            return project_id

        except Exception as e:
            logger.error(f"Auto-selection failed: {e}")
            return None

    def increment_memory_count(self, project_id: str) -> None:
        """
        Increment memory count for a project

        Args:
            project_id: Project ID

        Note:
            Called when a memory is associated with this project.
        """
        self.project_storage.increment_memory_count(project_id)

    def decrement_memory_count(self, project_id: str) -> None:
        """
        Decrement memory count for a project

        Args:
            project_id: Project ID

        Note:
            Called when a memory is removed from this project.
        """
        self.project_storage.decrement_memory_count(project_id)

    def get_project_stats(self, project_id: str) -> Optional[Dict[str, Any]]:
        """
        Get statistics for a project

        Args:
            project_id: Project ID

        Returns:
            Dict with stats (memory_count, created_at, last_accessed, etc.),
            or None if project not found
        """
        project = self.project_storage.load_project(project_id)

        if not project:
            return None

        return {
            'project_id': project.id,
            'name': project.name,
            'memory_count': project.memory_count,
            'created_at': project.created_at.isoformat(),
            'last_accessed': project.last_accessed.isoformat(),
            'tags': project.tags,
            'description': project.description
        }

    def _build_project_context(self, projects: List[Project]) -> str:
        """
        Build context string from project list for LLM

        Args:
            projects: List of Project instances

        Returns:
            Formatted context string
        """
        lines = []

        for project in projects[:10]:  # Limit to top 10 recent projects
            tags_str = ", ".join(project.tags) if project.tags else "no tags"
            lines.append(f"- ID: {project.id}, Name: {project.name}, Tags: [{tags_str}], Description: {project.description}")

        return "\n".join(lines)

    def _build_selection_prompt(self, query: str, project_context: str) -> str:
        """
        Build prompt for project auto-selection

        Args:
            query: User query
            project_context: Formatted project context

        Returns:
            LLM prompt string
        """
        prompt = f"""Given a user query, select the most relevant project from the list.
If no project is clearly relevant, respond with "NONE".

Available Projects:
{project_context}

User Query: {query}

Respond with only the Project ID (e.g., "abc123-def456-...") or "NONE".
"""
        return prompt

    def _parse_selection_response(self, response: str, projects: List[Project]) -> Optional[str]:
        """
        Parse LLM response to extract project ID

        Args:
            response: LLM response text
            projects: List of available projects

        Returns:
            Project ID if valid match found, None otherwise
        """
        response = response.strip()

        # Check for "NONE" response
        if response.upper() == "NONE":
            return None

        # Check if response matches any project ID
        project_ids = {project.id for project in projects}

        if response in project_ids:
            return response

        # Fallback: check if response contains a project ID
        for project_id in project_ids:
            if project_id in response:
                return project_id

        return None
