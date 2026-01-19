"""OpenAI LLM provider implementation."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

import httpx

from tweetdna.providers.base import LLMProvider


class OpenAIProvider(LLMProvider):
    """
    OpenAI API provider.
    
    Supports both text generation and structured JSON output.
    Uses httpx for HTTP requests to avoid SDK dependency bloat.
    """

    BASE_URL = "https://api.openai.com/v1"

    def __init__(self, api_key: str, default_model: str = "gpt-4o-mini"):
        self.api_key = api_key
        self.default_model = default_model
        self._client = httpx.Client(
            base_url=self.BASE_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=60.0,
        )

    @property
    def name(self) -> str:
        return "openai"

    def generate_text(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> str:
        """Generate text using OpenAI chat completion."""
        model = model or self.default_model

        # TODO: Add actual API call when credentials are available
        # For now, stub the response to allow local testing
        if not self.api_key or self.api_key == "stub":
            return self._stub_text_response(prompt)

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        response = self._client.post("/chat/completions", json=payload)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

    def generate_json(
        self,
        prompt: str,
        schema: Dict[str, Any],
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> Dict[str, Any]:
        """Generate structured JSON using OpenAI with response_format."""
        model = model or self.default_model

        # TODO: Add actual API call when credentials are available
        if not self.api_key or self.api_key == "stub":
            return self._stub_json_response(prompt, schema)

        # Use JSON mode for structured output
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": "You must respond with valid JSON only. No other text.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"},
        }

        response = self._client.post("/chat/completions", json=payload)
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"]
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
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self) -> "OpenAIProvider":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
