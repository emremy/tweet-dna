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

# Reply intent options (algorithm-aware)
ReplyIntent = Literal[
    "agree_extend",      # agree AND add something new
    "disagree_reason",   # disagree with specific reasoning
    "add_context",       # provide relevant info they missed
    "share_experience",  # relate a personal story/example
    "challenge",         # push back on a specific point
    "joke",              # humor that relates to their content
    "react",             # genuine emotional response
]

# Expected engagement type
ExpectedEngagement = Literal["reply", "like", "repost", "mixed"]

# Risk levels
RiskLevel = Literal["low", "medium", "high"]

# Conversation value levels
ConversationValue = Literal["low", "medium", "high"]


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
    reply_intent: Optional[str] = None   # Reply intent (agree_extend, disagree_reason, etc.)
    
    # Algorithm alignment fields (additive, backward-compatible)
    expected_engagement: Optional[ExpectedEngagement] = None  # reply|like|repost|mixed
    suppression_risk: Optional[RiskLevel] = None              # low|medium|high
    algorithm_alignment_notes: Optional[str] = None           # Brief note on ranking signals
    conversation_value: Optional[ConversationValue] = None    # low|medium|high
    
    # Thread-specific algorithm fields
    hook_strength: Optional[str] = None        # weak|moderate|strong (for threads)
    density_validated: Optional[bool] = None   # Whether density check passed
    unique_value: Optional[str] = None         # What unique value this item adds


class PersonaAlgorithmConflict(BaseModel):
    """Records a conflict between persona rules and algorithm constraints."""
    
    persona_rule: str           # Which persona rule conflicted
    algorithm_constraint: str   # Which algorithm rule overrode it
    resolution: str             # How the conflict was resolved


class ReviewResult(BaseModel):
    """Result from reviewing a draft against the persona and algorithm."""

    draft_id: UUID
    alignment_score: float = Field(ge=0.0, le=100.0)
    violations: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)
    revised_text: Optional[str] = None
    
    # Algorithm alignment fields (additive, backward-compatible)
    algorithm_alignment_score: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    suppression_risk_score: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    repetition_risk: Optional[RiskLevel] = None
    conversation_value: Optional[ConversationValue] = None
    algorithm_issues: List[str] = Field(default_factory=list)
    
    # Persona-algorithm conflict resolution
    persona_algorithm_conflicts: List[PersonaAlgorithmConflict] = Field(default_factory=list)
    revision_reason: Optional[str] = None  # Why revision was needed