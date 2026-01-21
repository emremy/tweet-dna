"""Local LLM provider (Ollama-compatible HTTP interface)."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

import httpx

from tweetdna.providers.base import LLMProvider


class LocalProvider(LLMProvider):
    """
    Local LLM provider using Ollama-compatible HTTP API.
    
    Compatible with:
    - Ollama (http://localhost:11434)
    - LM Studio
    - Any OpenAI-compatible local server
    """

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:11434",
        default_model: str = "llama3",
    ):
        self.base_url = base_url.rstrip("/")
        self.default_model = default_model
        self._client = httpx.Client(
            timeout=120.0,  # Local models can be slow
        )

    @property
    def name(self) -> str:
        return "local"

    def _is_ollama(self) -> bool:
        """Check if the endpoint is Ollama (uses /api/generate)."""
        return "11434" in self.base_url

    def generate_text(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> str:
        """Generate text using local LLM."""
        model = model or self.default_model

        if self._is_ollama():
            return self._ollama_generate(prompt, model, temperature, max_tokens)
        else:
            return self._openai_compatible_generate(prompt, model, temperature, max_tokens)

    def generate_json(
        self,
        prompt: str,
        schema: Dict[str, Any],
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 8192,
    ) -> Dict[str, Any]:
        """
        Generate structured JSON using local LLM.
        
        Note: Most local models don't support structured output natively,
        so we request JSON in the prompt and parse defensively.
        """
        model = model or self.default_model

        # Wrap prompt with JSON instruction
        json_prompt = f"""You must respond with valid JSON only. No other text or explanation.

{prompt}

Respond with JSON only:"""

        if self._is_ollama():
            response = self._ollama_generate(json_prompt, model, temperature, max_tokens)
        else:
            response = self._openai_compatible_generate(json_prompt, model, temperature, max_tokens)

        return self._parse_json_response(response)

    def _ollama_generate(
        self,
        prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        """Generate using Ollama API."""
        url = f"{self.base_url}/api/generate"

        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        try:
            response = self._client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("response", "")
        except httpx.ConnectError:
            # Return stub if Ollama is not running
            return self._stub_response(prompt)
        except Exception as e:
            return f"Error: {e}. Ensure Ollama is running."

    def _openai_compatible_generate(
        self,
        prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        """Generate using OpenAI-compatible API (LM Studio, etc.)."""
        url = f"{self.base_url}/v1/chat/completions"

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        try:
            response = self._client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except httpx.ConnectError:
            return self._stub_response(prompt)
        except Exception as e:
            return f"Error: {e}. Ensure local LLM server is running."

    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """Parse JSON from LLM response, handling common issues."""
        # Try direct parse first
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass

        # Try to extract JSON from markdown code blocks
        if "```json" in response:
            start = response.find("```json") + 7
            end = response.find("```", start)
            if end > start:
                try:
                    return json.loads(response[start:end].strip())
                except json.JSONDecodeError:
                    pass

        # Try to find JSON object in response
        start = response.find("{")
        end = response.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(response[start:end])
            except json.JSONDecodeError:
                pass

        # Return error object if all parsing fails
        return {"error": "Failed to parse JSON", "raw": response[:500]}

    def _stub_response(self, prompt: str) -> str:
        """Return stub response when local LLM is not available."""
        if "persona" in prompt.lower():
            return json.dumps({
                "version": 1,
                "display_name": "Local Stub Persona",
                "voice_rules": {
                    "sentence_length": "short",
                    "hook_styles": ["observation"],
                    "humor_style": ["dry"],
                    "jargon_level": "medium",
                    "directness": "high",
                },
                "tone": {"spice_default": "medium", "safe_mode": True},
                "topics": [{"name": "general", "weight": 1.0}],
                "formatting": {
                    "emoji_rate": "low",
                    "punctuation_style": "minimal",
                    "line_breaks": "rare",
                },
                "constraints": {"no_slurs": True, "no_threats": True, "max_chars": 280},
                "examples": {"signature_patterns": ["Short and direct."]},
            })

        return "Stub: Local LLM not available. Start Ollama or configure LOCAL_LLM_BASE_URL."

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self) -> "LocalProvider":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
