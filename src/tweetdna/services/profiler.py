"""Profiler service for building persona from tweets."""

from __future__ import annotations

import hashlib
from typing import Any, Optional

from tweetdna.prompts import build_profile_prompt
from tweetdna.providers.base import LLMProvider
from tweetdna.schemas import Persona
from tweetdna.storage import Repository


class ProfilerService:
    """
    Service for building persona profiles from historical tweets.
    
    This is the ONLY place where full tweet history is sent to the LLM.
    The resulting persona is stored and reused for all subsequent generation.
    """

    def __init__(self, repository: Repository, provider: LLMProvider):
        self.repository = repository
        self.provider = provider

    def build_persona(
        self,
        sample_size: int = 300,
        bio: Optional[str] = None,
        pinned_tweet: Optional[str] = None,
        force: bool = False,
    ) -> Persona:
        """
        Build a persona from sampled tweets.
        
        Args:
            sample_size: Number of tweets to sample (200-400 recommended)
            bio: Optional user bio text
            pinned_tweet: Optional pinned tweet text
            force: Force rebuild even if persona exists
            
        Returns:
            Validated Persona object
        """
        # Check existing persona
        if not force:
            existing = self.repository.get_latest_persona()
            if existing:
                return existing

        # Sample tweets for profiling
        tweets = self.repository.sample_tweets_for_profiling(sample_size)
        if not tweets:
            raise ValueError("No tweets available for profiling. Run 'tweetdna fetch' first.")

        # Build the profiling prompt - this sends tweets to LLM ONCE
        prompt = build_profile_prompt(
            tweets=tweets,
            bio=bio,
            pinned_tweet=pinned_tweet,
        )

        # Get persona JSON schema for structured output
        persona_schema = Persona.model_json_schema()

        # Generate persona via LLM
        result = self.provider.generate_json(
            prompt=prompt,
            schema=persona_schema,
            temperature=0.2,  # Low temperature for deterministic output
        )

        # Validate and create persona
        persona = Persona.model_validate(result)

        # Save to database
        version = self.repository.save_persona(persona)
        persona.version = version

        return persona

    def get_current_persona(self) -> Optional[Persona]:
        """Get the current persona without rebuilding."""
        return self.repository.get_latest_persona()
