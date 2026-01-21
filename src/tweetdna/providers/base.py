"""Base LLM provider interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class LLMProvider(ABC):
    """
    Abstract base class for LLM providers.
    
    All providers must implement these two methods:
    - generate_text: For free-form text generation
    - generate_json: For structured JSON output with schema validation
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the provider name."""
        ...

    @abstractmethod
    def generate_text(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> str:
        """
        Generate text from a prompt.
        
        Args:
            prompt: The input prompt
            model: Model name override (uses default if None)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated text
        """
        ...

    @abstractmethod
    def generate_json(
        self,
        prompt: str,
        schema: Dict[str, Any],
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 8192,
    ) -> Dict[str, Any]:
        """
        Generate structured JSON output.
        
        Args:
            prompt: The input prompt
            schema: JSON schema for validation
            model: Model name override (uses default if None)
            temperature: Sampling temperature (lower for deterministic output)
            max_tokens: Maximum tokens to generate
            
        Returns:
            Parsed and validated JSON dict
        """
        ...
