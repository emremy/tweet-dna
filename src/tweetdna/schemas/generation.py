"""Generation and review schema definitions."""

from __future__ import annotations

from typing import List, Literal, Optional, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

SpiceLevel = Literal["low", "medium", "high"]
GenerationKind = Literal["tweet", "thread_outline", "thread_draft", "reply"]

# Reply emotion/tone options
ReplyTone = Literal[
    "neutral",      # balanced, conversational
    "supportive",   # encouraging, agreeing, positive
    "curious",      # asking follow-ups, interested
    "playful",      # teasing, witty, light humor
    "sarcastic",    # dry humor, ironic
    "critical",     # disagreeing, pushing back (respectfully)
    "angry",        # frustrated, calling out (within persona)
    "excited",      # enthusiastic, hyped
    "thoughtful",   # adding nuance, reflective
]


class Draft(BaseModel):
    """A generated draft (tweet or thread item)."""

    id: UUID = Field(default_factory=uuid4)
    kind: GenerationKind = "tweet"
    topic: str
    text: Union[str, List[str]]  # str for tweet, list for thread
    tags: List[str] = Field(default_factory=list)
    spice: SpiceLevel = "medium"
    persona_version: int
    rationale: str = ""
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    alignment_score: Optional[float] = None
    notes: Optional[str] = None
    # Reply-specific fields
    reply_to_text: Optional[str] = None  # Original tweet being replied to
    reply_tone: Optional[str] = None     # Emotion/tone used


class ReviewResult(BaseModel):
    """Result from reviewing a draft against the persona."""

    draft_id: UUID
    alignment_score: float = Field(ge=0.0, le=100.0)
    violations: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)
    revised_text: Optional[str] = None
