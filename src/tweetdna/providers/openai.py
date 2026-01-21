"""OpenAI LLM provider implementation using official OpenAI SDK."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

from openai import OpenAI

from tweetdna.providers.base import LLMProvider


class OpenAIProvider(LLMProvider):
    """
    OpenAI API provider using official OpenAI Python SDK.
    
    Supports both text generation and structured JSON output.
    """
    
    # Models that don't support custom temperature (only default=1)
    NO_TEMPERATURE_MODELS = ("gpt-5", "o1", "o3")

    def __init__(self, api_key: str, default_model: str = "gpt-5.2-mini"):
        self.api_key = api_key
        self.default_model = default_model
        self._client: Optional[OpenAI] = None
        
        # Initialize client only if we have a valid API key
        if api_key and api_key != "stub":
            self._client = OpenAI(
                api_key=api_key,
                timeout=60.0,
            )

    @property
    def name(self) -> str:
        return "openai"
    
    def _supports_temperature(self, model: str) -> bool:
        """Check if model supports custom temperature values."""
        model_lower = model.lower()
        return not any(model_lower.startswith(prefix) for prefix in self.NO_TEMPERATURE_MODELS)

    def generate_text(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> str:
        """Generate text using OpenAI chat completion."""
        model = model or self.default_model

        # Return stub if no valid client
        if self._client is None:
            return self._stub_text_response(prompt)

        # Build kwargs - only include temperature if model supports it
        kwargs: Dict[str, Any] = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_completion_tokens": max_tokens,
        }
        if self._supports_temperature(model):
            kwargs["temperature"] = temperature

        response = self._client.chat.completions.create(**kwargs)
        
        return response.choices[0].message.content or ""

    def generate_json(
        self,
        prompt: str,
        schema: Dict[str, Any],
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 8192,
    ) -> Dict[str, Any]:
        """Generate structured JSON using OpenAI with response_format."""
        model = model or self.default_model

        # Return stub if no valid client
        if self._client is None:
            return self._stub_json_response(prompt, schema)

        # Build kwargs - only include temperature if model supports it
        kwargs: Dict[str, Any] = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": "You must respond with valid JSON only. No other text.",
                },
                {"role": "user", "content": prompt},
            ],
            "max_completion_tokens": max_tokens,
            "response_format": {"type": "json_object"},
        }
        if self._supports_temperature(model):
            kwargs["temperature"] = temperature

        response = self._client.chat.completions.create(**kwargs)
        
        content = response.choices[0].message.content or "{}"
        return json.loads(content)

    def _stub_text_response(self, prompt: str) -> str:
        """Return a stub response for testing without API credentials."""
        if "review" in prompt.lower():
            return json.dumps({
                "alignment_score": 85,
                "violations": [],
                "suggestions": ["Consider adding more personality"],
                "revised_text": None,
            })
        return "This is a stub response. Set OPENAI_API_KEY to enable real generation."

    def _stub_json_response(self, prompt: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Return a stub JSON response matching the expected schema."""
        # Check if this is a persona profiling request
        if "persona" in prompt.lower() and "voice_rules" in str(schema):
            return {
                "version": 1,
                "display_name": "Stub Persona",
                "voice_rules": {
                    "sentence_length": "short",
                    "hook_styles": ["observation", "contrarian"],
                    "humor_style": ["dry"],
                    "jargon_level": "medium",
                    "directness": "high",
                },
                "tone": {"spice_default": "medium", "safe_mode": True},
                "topics": [
                    {"name": "technology", "weight": 0.4},
                    {"name": "productivity", "weight": 0.3},
                ],
                "formatting": {
                    "emoji_rate": "low",
                    "punctuation_style": "minimal",
                    "line_breaks": "rare",
                },
                "constraints": {"no_slurs": True, "no_threats": True, "max_chars": 280},
                "examples": {
                    "signature_patterns": [
                        "Short opener. Hard truth.",
                        "One-liner with punch.",
                    ]
                },
            }

        # Check if this is a generation request
        if "generate" in prompt.lower() or "draft" in prompt.lower():
            return {
                "drafts": [
                    {
                        "text": "Stub draft: Your real content will appear here.",
                        "tags": ["stub", "test"],
                        "rationale": "This is a placeholder draft.",
                        "confidence": 0.8,
                    }
                ]
            }

        # Default stub response
        return {"status": "stub", "message": "Set API key for real responses"}

    def close(self) -> None:
        """Close the OpenAI client."""
        if self._client is not None:
            self._client.close()

    def __enter__(self) -> "OpenAIProvider":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
