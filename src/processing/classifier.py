#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Schema Classifier

Classifies conversations and content into schema types:
- Incident: Bug reports, errors, troubleshooting
- Snippet: Code examples with usage context
- Decision: Architectural choices, trade-offs
- Process: Thought processes, learning, experimentation

Uses local LLM (qwen2.5:7b) for privacy-preserving classification.

Requirements: Requirement 2 (MVP - Schema Classification)
"""

from typing import Dict, Any, Optional
import logging
import re

from src.models import ModelRouter, SchemaType

logger = logging.getLogger(__name__)


class SchemaClassifier:
    """
    Classifier for conversation schemas

    Uses local LLM to classify content into one of four schema types.
    Classification is always done locally to preserve privacy.

    Attributes:
        model_router: ModelRouter instance for LLM access
    """

    def __init__(self, model_router: ModelRouter):
        """
        Initialize Schema Classifier

        Args:
            model_router: ModelRouter instance
        """
        self.model_router = model_router
        logger.info("Initialized SchemaClassifier")

    def classify(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> SchemaType:
        """
        Classify content into schema type

        Args:
            content: Content to classify (conversation or text)
            metadata: Optional metadata (may contain hints)

        Returns:
            SchemaType enum value

        Example:
            >>> classifier = SchemaClassifier(router)
            >>> schema = classifier.classify("Bug in login: returns 500 error")
            >>> print(schema)
            SchemaType.INCIDENT
        """
        # Build classification prompt
        prompt = self._build_classification_prompt(content, metadata)

        # Use local LLM for classification (privacy-critical, simple task)
        try:
            result = self.model_router.route(
                task_type='classification',
                prompt=prompt,
                max_tokens=10,  # Only need one word
                temperature=0.3  # Lower temperature for more deterministic results
            )

            # Parse result
            schema_type = self._parse_classification_result(result)

            logger.debug(f"Classified as {schema_type.value}: {content[:100]}...")
            return schema_type

        except Exception as e:
            logger.error(f"Classification failed: {e}")
            # Fallback to Process (most general schema)
            logger.warning("Falling back to Process schema")
            return SchemaType.PROCESS

    def classify_conversation(
        self,
        user_message: str,
        assistant_message: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> SchemaType:
        """
        Classify a conversation (User + Assistant exchange)

        Args:
            user_message: User's message
            assistant_message: Assistant's response
            metadata: Optional metadata

        Returns:
            SchemaType enum value

        Example:
            >>> classifier = SchemaClassifier(router)
            >>> schema = classifier.classify_conversation(
            ...     "Why is the login failing?",
            ...     "The issue is caused by..."
            ... )
        """
        # Combine into single content
        content = f"User: {user_message}\n\nAssistant: {assistant_message}"
        return self.classify(content, metadata)

    def _build_classification_prompt(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Build prompt for classification

        Args:
            content: Content to classify
            metadata: Optional metadata

        Returns:
            Classification prompt
        """
        prompt = """Classify the following content into ONE of these schema types.

Schema Types:
1. Incident - Bug reports, errors, troubleshooting, debugging, failures, exceptions
   Examples: "500 error when logging in", "NullPointerException in UserService"

2. Snippet - Code examples, implementations, code snippets with usage context
   Examples: "How to use React hooks", "Example of async/await in Python"

3. Decision - Architectural choices, design decisions, trade-offs, comparisons
   Examples: "Should we use Redis or Memcached?", "Choosing between REST and GraphQL"

4. Process - Thought processes, learning, experimentation, exploration, investigations
   Examples: "Trying different approaches to optimize queries", "Learning about Docker networking"

Content to classify:
---
{content}
---

Instructions:
- Respond with ONLY ONE WORD: Incident, Snippet, Decision, or Process
- Do not include explanations or additional text
- Be concise and definitive

Classification:"""

        return prompt.format(content=content[:2000])  # Limit content length

    def _parse_classification_result(self, result: str) -> SchemaType:
        """
        Parse LLM result into SchemaType

        Args:
            result: LLM output

        Returns:
            SchemaType enum value

        Raises:
            ValueError: If result cannot be parsed
        """
        # Clean result (remove whitespace, lowercase)
        cleaned = result.strip().lower()

        # Extract first word (in case LLM added extra text)
        first_word = cleaned.split()[0] if cleaned else ""

        # Map to SchemaType
        if "incident" in first_word:
            return SchemaType.INCIDENT
        elif "snippet" in first_word:
            return SchemaType.SNIPPET
        elif "decision" in first_word:
            return SchemaType.DECISION
        elif "process" in first_word:
            return SchemaType.PROCESS
        else:
            # Try fuzzy matching
            if any(keyword in cleaned for keyword in ["bug", "error", "fail", "exception", "crash"]):
                logger.debug("Fuzzy matched to Incident")
                return SchemaType.INCIDENT
            elif any(keyword in cleaned for keyword in ["code", "example", "snippet", "implementation"]):
                logger.debug("Fuzzy matched to Snippet")
                return SchemaType.SNIPPET
            elif any(keyword in cleaned for keyword in ["choose", "decision", "trade", "compare"]):
                logger.debug("Fuzzy matched to Decision")
                return SchemaType.DECISION
            else:
                logger.warning(f"Could not parse classification result: {result}")
                # Default to Process
                return SchemaType.PROCESS

    def classify_batch(
        self,
        contents: list[str],
        metadata_list: Optional[list[Dict[str, Any]]] = None
    ) -> list[SchemaType]:
        """
        Classify multiple contents (batch operation)

        Args:
            contents: List of contents to classify
            metadata_list: Optional list of metadata dicts (parallel to contents)

        Returns:
            List of SchemaType values

        Example:
            >>> classifier = SchemaClassifier(router)
            >>> schemas = classifier.classify_batch([
            ...     "Bug in login",
            ...     "How to use async/await"
            ... ])
            >>> print(schemas)
            [SchemaType.INCIDENT, SchemaType.SNIPPET]
        """
        if metadata_list is None:
            metadata_list = [None] * len(contents)

        results = []
        for content, metadata in zip(contents, metadata_list):
            schema = self.classify(content, metadata)
            results.append(schema)

        logger.info(f"Classified {len(results)} items")
        return results

    def get_schema_statistics(self, schema_types: list[SchemaType]) -> Dict[str, int]:
        """
        Get statistics for schema types

        Args:
            schema_types: List of SchemaType values

        Returns:
            Dict mapping schema type name to count

        Example:
            >>> schemas = [SchemaType.INCIDENT, SchemaType.INCIDENT, SchemaType.SNIPPET]
            >>> stats = classifier.get_schema_statistics(schemas)
            >>> print(stats)
            {'Incident': 2, 'Snippet': 1, 'Decision': 0, 'Process': 0}
        """
        stats = {
            'Incident': 0,
            'Snippet': 0,
            'Decision': 0,
            'Process': 0
        }

        for schema_type in schema_types:
            stats[schema_type.value] += 1

        return stats
