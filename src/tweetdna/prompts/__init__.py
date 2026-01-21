"""Prompt templates for TweetDNA."""

from tweetdna.prompts.templates import (
    # Prompt builders
    build_generation_prompt,
    build_profile_prompt,
    build_reply_prompt,
    build_review_prompt,
    build_thread_prompt,
    # Algorithm constants (derived from x-official-repo)
    ALGORITHM_CONSTRAINTS,
    ALGORITHM_NEGATIVE_SIGNALS,
    ALGORITHM_POSITIVE_SIGNALS,
    REPLY_ALGORITHM_RULES,
    REPLY_DEMOTION_PATTERNS,
    SUPPRESSION_TRIGGERS,
    THREAD_QUALITY_SIGNALS,
)

__all__ = [
    # Prompt builders
    "build_profile_prompt",
    "build_generation_prompt",
    "build_thread_prompt",
    "build_reply_prompt",
    "build_review_prompt",
    # Algorithm constants
    "ALGORITHM_POSITIVE_SIGNALS",
    "ALGORITHM_NEGATIVE_SIGNALS",
    "SUPPRESSION_TRIGGERS",
    "REPLY_DEMOTION_PATTERNS",
    "THREAD_QUALITY_SIGNALS",
    "ALGORITHM_CONSTRAINTS",
    "REPLY_ALGORITHM_RULES",
]
