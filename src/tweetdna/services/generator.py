"""Generator service for creating tweet and thread drafts."""

from __future__ import annotations

import hashlib
import json
from typing import Dict, List, Optional
from uuid import uuid4

from tweetdna.prompts import build_generation_prompt, build_reply_prompt, build_thread_prompt
from tweetdna.providers.base import LLMProvider
from tweetdna.schemas import Draft, Persona, ReplyTone, SpiceLevel
from tweetdna.storage import Repository


class GeneratorService:
    """
    Service for generating tweet and thread drafts.
    
    IMPORTANT: This service only sends the persona JSON to the LLM,
    NOT the full tweet history. Optional examples are limited to 3-5.
    """

    def __init__(self, repository: Repository, provider: LLMProvider):
        self.repository = repository
        self.provider = provider

    def generate_tweets(
        self,
        topic: str,
        n: int = 5,
        spice: SpiceLevel = "medium",
        min_chars: int = 0,
        max_chars: int = 280,
        use_examples: bool = False,
    ) -> List[Draft]:
        """
        Generate tweet drafts.
        
        Args:
            topic: Topic or prompt for generation
            n: Number of drafts to generate
            spice: Spice level (low/medium/high)
            min_chars: Minimum characters per tweet (0 = no minimum)
            max_chars: Maximum characters per tweet
            use_examples: Whether to retrieve similar historical tweets as references
            
        Returns:
            List of Draft objects
        """
        persona = self._get_required_persona()

        # Get optional examples (limited to 5)
        examples: Optional[List[str]] = None
        if use_examples:
            examples = self._retrieve_examples(topic, limit=5)

        # Build prompt - only sends persona, NOT full history
        prompt = build_generation_prompt(
            persona=persona,
            topic=topic,
            n=n,
            spice=spice,
            min_chars=min_chars,
            max_chars=max_chars,
            examples=examples,
        )

        # Generate via LLM
        result = self.provider.generate_json(
            prompt=prompt,
            schema={"type": "object"},  # Loose schema, we validate manually
            temperature=0.7,
        )

        # Parse and validate drafts
        drafts = self._parse_generation_result(
            result=result,
            topic=topic,
            spice=spice,
            persona_version=persona.version,
        )

        # Save to database
        prompt_hash = hashlib.md5(prompt.encode()).hexdigest()[:12]
        for draft in drafts:
            self.repository.save_generation(
                draft=draft,
                provider=self.provider.name,
                model="default",
                prompt_hash=prompt_hash,
            )

        return drafts

    def generate_thread(
        self,
        topic: str,
        tweet_count: int = 5,
        spice: SpiceLevel = "medium",
        full_draft: bool = False,
        min_chars: int = 0,
        max_chars: int = 280,
    ) -> List[Draft]:
        """
        Generate a thread outline or full thread drafts.
        
        Args:
            topic: Thread topic
            tweet_count: Number of tweets in thread
            spice: Spice level
            full_draft: Generate full drafts (True) or outline only (False)
            min_chars: Minimum characters per tweet (0 = no minimum)
            max_chars: Maximum characters per tweet
            
        Returns:
            List of Draft objects (one per thread item)
        """
        persona = self._get_required_persona()

        prompt = build_thread_prompt(
            persona=persona,
            topic=topic,
            tweet_count=tweet_count,
            spice=spice,
            full_draft=full_draft,
            min_chars=min_chars,
            max_chars=max_chars,
        )

        result = self.provider.generate_json(
            prompt=prompt,
            schema={"type": "object"},
            temperature=0.7,
        )

        drafts = self._parse_thread_result(
            result=result,
            topic=topic,
            spice=spice,
            persona_version=persona.version,
            full_draft=full_draft,
        )

        prompt_hash = hashlib.md5(prompt.encode()).hexdigest()[:12]
        for draft in drafts:
            self.repository.save_generation(
                draft=draft,
                provider=self.provider.name,
                model="default",
                prompt_hash=prompt_hash,
            )

        return drafts

    def generate_replies(
        self,
        original_tweet: str,
        tone: ReplyTone = "neutral",
        n: int = 3,
        min_chars: int = 0,
        max_chars: int = 280,
        context: Optional[str] = None,
    ) -> List[Draft]:
        """
        Generate reply drafts to an existing tweet.
        
        Args:
            original_tweet: The tweet text being replied to
            tone: Emotional tone for the reply (neutral, supportive, angry, etc.)
            n: Number of reply drafts to generate
            min_chars: Minimum characters per reply (0 = no minimum)
            max_chars: Maximum characters per reply
            context: Optional additional context (who posted, thread context, etc.)
            
        Returns:
            List of Draft objects
        """
        persona = self._get_required_persona()

        prompt = build_reply_prompt(
            persona=persona,
            original_tweet=original_tweet,
            tone=tone,
            n=n,
            min_chars=min_chars,
            max_chars=max_chars,
            context=context,
        )

        result = self.provider.generate_json(
            prompt=prompt,
            schema={"type": "object"},
            temperature=0.7,
        )

        drafts = self._parse_reply_result(
            result=result,
            original_tweet=original_tweet,
            tone=tone,
            persona_version=persona.version,
        )

        prompt_hash = hashlib.md5(prompt.encode()).hexdigest()[:12]
        for draft in drafts:
            self.repository.save_generation(
                draft=draft,
                provider=self.provider.name,
                model="default",
                prompt_hash=prompt_hash,
            )

        return drafts

    def _get_required_persona(self) -> Persona:
        """Get persona or raise error if not available."""
        persona = self.repository.get_latest_persona()
        if not persona:
            raise ValueError("No persona found. Run 'tweetdna profile' first.")
        return persona

    def _retrieve_examples(self, topic: str, limit: int = 5) -> List[str]:
        """
        Retrieve similar historical tweets as examples.
        
        Uses simple lexical matching. Could be enhanced with embeddings.
        """
        # Simple approach: get recent tweets and filter by keyword overlap
        tweets = self.repository.get_tweets(limit=100)
        
        topic_words = set(topic.lower().split())
        scored: List[tuple] = []
        
        for tweet in tweets:
            text = tweet.get("text", "").lower()
            tweet_words = set(text.split())
            overlap = len(topic_words & tweet_words)
            if overlap > 0:
                scored.append((overlap, tweet["text"]))
        
        # Sort by overlap and return top matches
        scored.sort(key=lambda x: x[0], reverse=True)
        return [text for _, text in scored[:limit]]

    def _parse_generation_result(
        self,
        result: Dict,
        topic: str,
        spice: SpiceLevel,
        persona_version: int,
    ) -> List[Draft]:
        """Parse LLM generation result into Draft objects."""
        drafts: List[Draft] = []
        raw_drafts = result.get("drafts", [])

        for item in raw_drafts:
            draft = Draft(
                id=uuid4(),
                kind="tweet",
                topic=topic,
                text=item.get("text", ""),
                tags=item.get("tags", []),
                spice=spice,
                persona_version=persona_version,
                rationale=item.get("rationale", ""),
                confidence=item.get("confidence", 0.8),
            )
            drafts.append(draft)

        return drafts

    def _parse_thread_result(
        self,
        result: Dict,
        topic: str,
        spice: SpiceLevel,
        persona_version: int,
        full_draft: bool,
    ) -> List[Draft]:
        """Parse LLM thread result into Draft objects."""
        drafts: List[Draft] = []
        raw_thread = result.get("thread", [])
        kind = "thread_draft" if full_draft else "thread_outline"

        for item in raw_thread:
            draft = Draft(
                id=uuid4(),
                kind=kind,
                topic=topic,
                text=item.get("text", ""),
                tags=[item.get("purpose", "body")],
                spice=spice,
                persona_version=persona_version,
                rationale=result.get("rationale", ""),
            )
            drafts.append(draft)

        return drafts

    def _parse_reply_result(
        self,
        result: Dict,
        original_tweet: str,
        tone: ReplyTone,
        persona_version: int,
    ) -> List[Draft]:
        """Parse LLM reply result into Draft objects."""
        drafts: List[Draft] = []
        raw_replies = result.get("replies", [])

        for item in raw_replies:
            draft = Draft(
                id=uuid4(),
                kind="reply",
                topic=f"reply:{original_tweet[:50]}...",  # Truncate for storage
                text=item.get("text", ""),
                tags=[item.get("approach", "react")],
                spice="medium",  # Replies don't use spice level
                persona_version=persona_version,
                rationale=item.get("rationale", ""),
                confidence=item.get("confidence", 0.8),
                reply_to_text=original_tweet,
                reply_tone=tone,
            )
            drafts.append(draft)

        return drafts
