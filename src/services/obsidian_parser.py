#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Obsidian Parser

Parses conversation notes from Obsidian Markdown files.
Extracts User/Assistant turns and Wikilinks for memory ingestion.

Requirements: Requirements 1.5, 9 (Obsidian Integration)
"""

import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class ObsidianParser:
    """
    Parser for Obsidian conversation notes

    Extracts structured conversations from Markdown files with:
    - User/Assistant turn patterns (**User:** / **Assistant:**)
    - Wikilinks ([[filename]])
    - YAML frontmatter (tags, date, etc.)

    Attributes:
        conversation_pattern: Regex pattern for conversation turns
        wikilink_pattern: Regex pattern for Wikilinks
    """

    # Regex patterns
    CONVERSATION_PATTERN = re.compile(
        r'\*\*User:\*\*\s*(.*?)\s*\*\*Assistant:\*\*\s*(.*?)(?=\*\*User:\*\*|\Z)',
        re.DOTALL | re.IGNORECASE
    )

    WIKILINK_PATTERN = re.compile(r'\[\[([^\]]+)\]\]')

    YAML_FRONTMATTER_PATTERN = re.compile(
        r'^---\s*\n(.*?)\n---\s*\n',
        re.DOTALL
    )

    def __init__(self):
        """Initialize Obsidian Parser"""
        logger.info("Initialized ObsidianParser")

    def parse_file(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Parse an Obsidian Markdown file

        Args:
            file_path: Path to the .md file

        Returns:
            Parsed data dict or None if no conversations found:
                - conversations: List[Dict] (user, assistant, index)
                - wikilinks: List[str] (linked file names)
                - metadata: Dict (YAML frontmatter)
                - file_path: str (original file path)
                - timestamp: str (ISO 8601)

        Example:
            >>> parser = ObsidianParser()
            >>> data = parser.parse_file('notes/conversation.md')
            >>> print(data['conversations'][0]['user'])
            How to fix TypeError?
        """
        try:
            # Read file
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Extract conversations
            conversations = self._extract_conversations(content)

            if not conversations:
                logger.debug(f"No conversations found in: {file_path}")
                return None

            # Extract Wikilinks
            wikilinks = self._extract_wikilinks(content)

            # Extract YAML frontmatter
            metadata = self._extract_frontmatter(content)

            # Build result
            result = {
                'conversations': conversations,
                'wikilinks': wikilinks,
                'metadata': metadata,
                'file_path': str(file_path),
                'timestamp': datetime.now().isoformat()
            }

            logger.info(
                f"Parsed {len(conversations)} conversation(s) from: {file_path}"
            )

            return result

        except UnicodeDecodeError as e:
            logger.error(f"Failed to decode file (not UTF-8): {file_path} - {e}")
            return None

        except Exception as e:
            logger.error(f"Failed to parse file: {file_path} - {e}")
            return None

    def _extract_conversations(self, content: str) -> List[Dict[str, Any]]:
        """
        Extract conversation turns from content

        Args:
            content: Markdown content

        Returns:
            List of conversation dicts (user, assistant, index)
        """
        conversations = []

        matches = self.CONVERSATION_PATTERN.finditer(content)

        for idx, match in enumerate(matches):
            user_msg = match.group(1).strip()
            assistant_msg = match.group(2).strip()

            if user_msg and assistant_msg:
                conversations.append({
                    'user': user_msg,
                    'assistant': assistant_msg,
                    'index': idx
                })

        return conversations

    def _extract_wikilinks(self, content: str) -> List[str]:
        """
        Extract Wikilinks from content

        Args:
            content: Markdown content

        Returns:
            List of linked file names
        """
        matches = self.WIKILINK_PATTERN.findall(content)

        # Clean up links (remove aliases, e.g., [[file|alias]] -> file)
        wikilinks = []
        for link in matches:
            # Handle aliases
            if '|' in link:
                link = link.split('|')[0]

            # Handle sections
            if '#' in link:
                link = link.split('#')[0]

            wikilinks.append(link.strip())

        return list(set(wikilinks))  # Remove duplicates

    def _extract_frontmatter(self, content: str) -> Dict[str, Any]:
        """
        Extract YAML frontmatter from content

        Args:
            content: Markdown content

        Returns:
            Metadata dict
        """
        match = self.YAML_FRONTMATTER_PATTERN.match(content)

        if not match:
            return {}

        frontmatter_text = match.group(1)

        # Parse YAML manually (simple key: value format)
        metadata = {}

        for line in frontmatter_text.split('\n'):
            line = line.strip()

            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()

                # Handle lists (tags: [tag1, tag2])
                if value.startswith('[') and value.endswith(']'):
                    value = [v.strip() for v in value[1:-1].split(',')]

                metadata[key] = value

        return metadata

    def is_conversation_note(self, file_path: str) -> bool:
        """
        Check if file contains conversation patterns

        Args:
            file_path: Path to the .md file

        Returns:
            True if file contains conversation patterns
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Quick check for conversation pattern
            return bool(self.CONVERSATION_PATTERN.search(content))

        except Exception as e:
            logger.error(f"Failed to check file: {file_path} - {e}")
            return False
