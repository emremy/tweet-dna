"""Persona schema definitions."""

from __future__ import annotations

from typing import List, Literal

from pydantic import BaseModel, Field


class VoiceRules(BaseModel):
    """Voice characteristics extracted from historical tweets."""

    sentence_length: Literal["short", "medium", "long"] = "medium"
    hook_styles: List[str] = Field(default_factory=list)
    humor_style: List[str] = Field(default_factory=list)
    jargon_level: Literal["low", "medium", "high"] = "medium"
    directness: Literal["low", "medium", "high"] = "high"


class Tone(BaseModel):
    """Tone settings for content generation."""

    spice_default: Literal["low", "medium", "high"] = "medium"
    safe_mode: bool = True


class Topic(BaseModel):
    """A weighted topic the persona covers."""

    name: str
    weight: float = Field(ge=0.0, le=1.0)


class Formatting(BaseModel):
    """Formatting preferences extracted from historical tweets."""

    emoji_rate: Literal["none", "low", "medium", "high"] = "low"
    punctuation_style: Literal["minimal", "standard", "expressive"] = "minimal"
    line_breaks: Literal["none", "rare", "frequent"] = "rare"


class Constraints(BaseModel):
    """Hard constraints for content generation."""

    no_slurs: bool = True
    no_threats: bool = True
    max_chars: int = 280


class Examples(BaseModel):
    """Example patterns from the persona's writing style."""

    signature_patterns: List[str] = Field(default_factory=list)


class Persona(BaseModel):
    """
    Complete persona schema validated by Pydantic.
    
    This is the core data structure sent to the LLM during generation.
    It must be compact and contain distilled patterns, not full tweet history.
    """

    version: int = 1
    display_name: str = "Account DNA"
    voice_rules: VoiceRules = Field(default_factory=VoiceRules)
    tone: Tone = Field(default_factory=Tone)
    topics: List[Topic] = Field(default_factory=list)
    formatting: Formatting = Field(default_factory=Formatting)
    constraints: Constraints = Field(default_factory=Constraints)
    examples: Examples = Field(default_factory=Examples)

    def to_prompt_context(self) -> str:
        """Convert persona to a string suitable for LLM prompts."""
        return self.model_dump_json(indent=2)
