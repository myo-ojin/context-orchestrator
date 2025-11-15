#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Model Router

Routes tasks to appropriate LLM (local vs cloud) based on complexity.
Optimizes for cost (use free local models) and quality (use cloud for complex tasks).

Requirements: Requirement 10 (MVP - Model Routing)
"""

from typing import Optional, List, Any, Dict
import logging

from .local_llm import LocalLLMClient
from .cli_llm import CLILLMClient

logger = logging.getLogger(__name__)


class ModelRouter:
    """
    Router for selecting appropriate LLM based on task complexity

    Routes tasks between local LLM (Ollama) and cloud LLM (via CLI)
    to optimize for privacy, cost, and quality.

    Routing strategy:
    - Embedding: Always local (privacy-critical, high-frequency)
    - Classification: Always local (simple task, privacy-critical)
    - Short summaries (<100 tokens): Local (sufficient quality)
    - Long summaries (>500 tokens): Cloud (high quality needed)
    - Complex reasoning: Cloud (complex task)

    Attributes:
        local_llm_client: LocalLLMClient instance
        cli_llm_client: CLILLMClient instance
        embedding_model: Model for embeddings (default: nomic-embed-text)
        inference_model: Model for local inference (default: qwen2.5:7b)
    """

    # Task routing configuration
    TASK_ROUTING = {
        'embedding': 'local',           # nomic-embed-text
        'classification': 'local',      # Qwen2.5-7B
        'short_summary': 'local',       # Qwen2.5-7B (<100 tokens)
        'long_summary': 'cloud',        # Claude/GPT (>500 tokens)
        'reasoning': 'cloud',           # Claude/GPT (complex reasoning)
        'consolidation': 'cloud',       # Claude/GPT (memory clustering)
    }

    def __init__(
        self,
        local_llm_client: LocalLLMClient,
        cli_llm_client: CLILLMClient,
        embedding_model: str = "nomic-embed-text",
        inference_model: str = "qwen2.5:7b",
        short_summary_max_tokens: int = 100,
        long_summary_min_tokens: int = 500,
    ):
        """
        Initialize Model Router

        Args:
            local_llm_client: LocalLLMClient instance
            cli_llm_client: CLILLMClient instance
            embedding_model: Embedding model name
            inference_model: Local inference model name
        """
        self.local_llm_client = local_llm_client
        self.cli_llm_client = cli_llm_client
        self.embedding_model = embedding_model
        self.inference_model = inference_model
        self.short_summary_max_tokens = short_summary_max_tokens
        self.long_summary_min_tokens = long_summary_min_tokens

        logger.info("Initialized ModelRouter")
        logger.info(f"  Embedding model: {embedding_model}")
        logger.info(f"  Inference model: {inference_model}")
        logger.info(
            f"  Routing thresholds: short<=%d, long>=%d"
            % (short_summary_max_tokens, long_summary_min_tokens)
        )

    def route(
        self,
        task_type: str,
        prompt: Optional[str] = None,
        text: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        timeout: int = 60,
        fallback_to_local: bool = True,
        force_routing: Optional[str] = None
    ) -> Any:
        """
        Route task to appropriate LLM

        Args:
            task_type: Task type ('embedding', 'classification', 'short_summary',
                       'long_summary', 'reasoning', 'consolidation')
            prompt: Input prompt (for generation tasks)
            text: Input text (for embedding tasks)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0-1.0)
            timeout: Timeout for cloud LLM calls
            fallback_to_local: Fallback to local on cloud failure

        Returns:
            Result from LLM (embedding vector for 'embedding', text for others)

        Raises:
            ValueError: If task_type is invalid or required params are missing

        Example:
            >>> router = ModelRouter(local_client, cli_client)
            >>> # Embedding (always local)
            >>> embedding = router.route('embedding', text="Hello world")
            >>> # Classification (always local)
            >>> schema = router.route('classification', prompt="Classify: Bug in login")
            >>> # Long summary (cloud)
            >>> summary = router.route('long_summary', prompt="Summarize: ...")
        """
        # Validate task type
        if task_type not in self.TASK_ROUTING:
            raise ValueError(
                f"Invalid task_type '{task_type}'. "
                f"Valid types: {list(self.TASK_ROUTING.keys())}"
            )

        # Determine routing
        routing = self.TASK_ROUTING[task_type]
        if force_routing:
            if force_routing not in ('local', 'cloud'):
                raise ValueError("force_routing must be 'local' or 'cloud'")
            routing = force_routing
        logger.debug(f"Routing task '{task_type}' to {routing}")

        # Handle embedding separately (different interface)
        if task_type == 'embedding':
            if text is None:
                raise ValueError("'text' is required for embedding task")
            return self._generate_embedding(text)

        # Handle generation tasks
        if prompt is None:
            raise ValueError(f"'prompt' is required for {task_type} task")

        # Route to local or cloud
        if routing == 'local':
            return self._generate_local(
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature
            )
        else:  # cloud
            try:
                return self._generate_cloud(
                    prompt=prompt,
                    timeout=timeout
                )
            except Exception as e:
                if fallback_to_local:
                    logger.warning(f"Cloud generation failed, falling back to local: {e}")
                    return self._generate_local(
                        prompt=prompt,
                        max_tokens=max_tokens,
                        temperature=temperature
                    )
                else:
                    raise

    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding (convenience method)

        Args:
            text: Input text

        Returns:
            Embedding vector

        Example:
            >>> router = ModelRouter(local_client, cli_client)
            >>> embedding = router.generate_embedding("Hello world")
        """
        return self.route(task_type='embedding', text=text)

    def classify_schema(self, content: str) -> str:
        """
        Classify memory schema (convenience method)

        Args:
            content: Content to classify

        Returns:
            Schema type (Incident/Snippet/Decision/Process)

        Example:
            >>> router = ModelRouter(local_client, cli_client)
            >>> schema = router.classify_schema("Bug in login flow")
            >>> print(schema)
            "Incident"
        """
        prompt = self._build_classification_prompt(content)
        return self.route(task_type='classification', prompt=prompt)

    def generate_summary(
        self,
        content: str,
        max_length: int = 100,
        use_cloud: Optional[bool] = None
    ) -> str:
        """
        Generate summary (convenience method)

        Args:
            content: Content to summarize
            max_length: Maximum summary length in tokens
            use_cloud: Force cloud usage (None = auto-decide based on length)

        Returns:
            Summary text

        Example:
            >>> router = ModelRouter(local_client, cli_client)
            >>> # Short summary (local)
            >>> summary = router.generate_summary(content, max_length=50)
            >>> # Long summary (cloud)
            >>> summary = router.generate_summary(content, max_length=500)
        """
        prompt = self._build_summary_prompt(content, max_length)

        # Auto-decide based on length if not specified
        if use_cloud is None:
            task_type = (
                'long_summary'
                if max_length and max_length >= self.long_summary_min_tokens
                else 'short_summary'
            )
        else:
            task_type = 'long_summary' if use_cloud else 'short_summary'

        return self.route(
            task_type=task_type,
            prompt=prompt,
            max_tokens=max_length
        )

    def _generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding using local model

        Args:
            text: Input text

        Returns:
            Embedding vector
        """
        logger.debug(f"Generating embedding for text: {text[:100]}...")
        return self.local_llm_client.generate_embedding(
            text=text,
            model=self.embedding_model
        )

    def _generate_local(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7
    ) -> str:
        """
        Generate text using local model

        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens
            temperature: Sampling temperature

        Returns:
            Generated text
        """
        logger.debug(f"Generating text with local model: {self.inference_model}")
        return self.local_llm_client.generate(
            prompt=prompt,
            model=self.inference_model,
            max_tokens=max_tokens,
            temperature=temperature
        )

    def _generate_cloud(
        self,
        prompt: str,
        timeout: int = 60
    ) -> str:
        """
        Generate text using cloud model via CLI

        Args:
            prompt: Input prompt
            timeout: Timeout in seconds

        Returns:
            Generated text
        """
        logger.debug("Generating text with cloud model via CLI")
        return self.cli_llm_client.generate(
            prompt=prompt,
            timeout=timeout
        )

    def _build_classification_prompt(self, content: str) -> str:
        """
        Build prompt for schema classification

        Args:
            content: Content to classify

        Returns:
            Classification prompt
        """
        return f"""Classify the following content into one of these schema types:
- Incident: Bug reports, errors, troubleshooting
- Snippet: Code examples with usage context
- Decision: Architectural choices, trade-offs
- Process: Thought processes, learning, experimentation

Content:
{content}

Respond with ONLY the schema type (Incident, Snippet, Decision, or Process).
Schema type:"""

    def _build_summary_prompt(self, content: str, max_length: int) -> str:
        """
        Build prompt for summarization

        Args:
            content: Content to summarize
            max_length: Maximum summary length

        Returns:
            Summarization prompt
        """
        return f"""Summarize the following content in {max_length} tokens or less.
Focus on the key points and actionable information.

Content:
{content}

Summary:"""

    def is_lightweight_task(self, task_type: str) -> bool:
        """
        Check if task should use local LLM

        Args:
            task_type: Task type

        Returns:
            True if task uses local LLM, False if cloud

        Example:
            >>> router = ModelRouter(local_client, cli_client)
            >>> router.is_lightweight_task('embedding')
            True
            >>> router.is_lightweight_task('long_summary')
            False
        """
        if task_type not in self.TASK_ROUTING:
            return False
        return self.TASK_ROUTING[task_type] == 'local'
