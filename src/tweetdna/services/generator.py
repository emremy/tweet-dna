"""Generator service for creating tweet and thread drafts."""

from __future__ import annotations

import hashlib
import json
from typing import Dict, List, Literal, Optional
from uuid import uuid4

from tweetdna.prompts import build_generation_prompt, build_reply_prompt, build_thread_prompt
from tweetdna.providers.base import LLMProvider
from tweetdna.schemas import Draft, Persona, ReplyTone, SpiceLevel
from tweetdna.storage import Repository

# Target engagement type for algorithm optimization
TargetEngagement = Literal["reply", "like", "repost", "mixed"]


class GeneratorService:
    """
    Service for generating tweet and thread drafts.
    
    IMPORTANT: This service only sends the persona JSON to the LLM,
    NOT the full tweet history. Optional examples are limited to 3-5.
    
    Algorithm-aware: Optimizes generation for X ranking signals.
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
        target_engagement: TargetEngagement = "reply",
    ) -> List[Draft]:
        """
        Generate tweet drafts with algorithm-aware optimization.
        
        Args:
            topic: Topic or prompt for generation
            n: Number of drafts to generate
            spice: Spice level (low/medium/high)
            min_chars: Minimum characters per tweet (0 = no minimum)
            max_chars: Maximum characters per tweet
            use_examples: Whether to retrieve similar historical tweets as references
            target_engagement: Target engagement type (reply|like|repost|mixed)
                - reply: Optimize for conversation starters (weighted heavily by algorithm)
                - like: Optimize for relatable, quotable content
                - repost: Optimize for share-worthy, informative content
                - mixed: Balanced approach
            
        Returns:
            List of Draft objects with algorithm alignment metadata
        """
        persona = self._get_required_persona()

        # Get optional examples (limited to 5)
        examples: Optional[List[str]] = None
        if use_examples:
            examples = self._retrieve_examples(topic, limit=5)

        # Build prompt - only sends persona, NOT full history
        # Now includes algorithm constraints and target engagement
        prompt = build_generation_prompt(
            persona=persona,
            topic=topic,
            n=n,
            spice=spice,
            min_chars=min_chars,
            max_chars=max_chars,
            examples=examples,
            target_engagement=target_engagement,
        )

        # Generate via LLM
        result = self.provider.generate_json(
            prompt=prompt,
            schema={"type": "object"},  # Loose schema, we validate manually
            temperature=0.7,
        )

        # Parse and validate drafts (now includes algorithm metadata)
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
        Generate a thread outline or full thread drafts with algorithm optimization.
        
        Algorithm-aware features:
        - Hook optimization: First tweet is optimized to stand alone
        - Density validation: Each tweet must add unique value
        - May return fewer tweets if content density is insufficient
        
        Args:
            topic: Thread topic
            tweet_count: Target number of tweets in thread (may be reduced for density)
            spice: Spice level
            full_draft: Generate full drafts (True) or outline only (False)
            min_chars: Minimum characters per tweet (0 = no minimum)
            max_chars: Maximum characters per tweet
            
        Returns:
            List of Draft objects (one per thread item) with algorithm metadata
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

        # Parse result with algorithm metadata
        drafts = self._parse_thread_result(
            result=result,
            topic=topic,
            spice=spice,
            persona_version=persona.version,
            full_draft=full_draft,
        )

        # Apply density validation - if LLM recommends fewer tweets, use that
        recommended_count = result.get("recommended_tweet_count", tweet_count)
        if recommended_count < len(drafts):
            drafts = drafts[:recommended_count]

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
        intent: Optional[str] = None,
    ) -> List[Draft]:
        """
        Generate reply drafts with algorithm-aware optimization.
        
        Algorithm-aware features:
        - Replies are first-class content, weighted heavily in ranking
        - Avoids low-effort patterns (generic praise, emoji-only, empty agreement)
        - Prioritizes conversation depth and distinct value
        
        Args:
            original_tweet: The tweet text being replied to
            tone: Emotional tone for the reply (neutral, supportive, angry, etc.)
            n: Number of reply drafts to generate
            min_chars: Minimum characters per reply (0 = no minimum)
            max_chars: Maximum characters per reply
            context: Optional additional context (who posted, thread context, etc.)
            intent: Optional reply intent to guide generation:
                - agree_extend: agree AND add something new
                - disagree_reason: disagree with specific reasoning
                - add_context: provide relevant info they missed
                - share_experience: relate a personal story/example
                - challenge: push back on a specific point
                - joke: humor that relates to their content
                - react: genuine emotional response
            
        Returns:
            List of Draft objects with algorithm metadata
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
            intent=intent,
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
        """Parse LLM generation result into Draft objects with algorithm metadata."""
        drafts: List[Draft] = []
        raw_drafts = result.get("drafts", [])

        for item in raw_drafts:
            # Parse algorithm alignment fields
            expected_engagement = item.get("expected_engagement")
            suppression_risk = item.get("suppression_risk")
            algorithm_notes = item.get("algorithm_alignment_notes")
            
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
                # Algorithm alignment fields
                expected_engagement=expected_engagement if expected_engagement in ["reply", "like", "repost", "mixed"] else None,
                suppression_risk=suppression_risk if suppression_risk in ["low", "medium", "high"] else None,
                algorithm_alignment_notes=algorithm_notes,
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
        """Parse LLM thread result into Draft objects with algorithm metadata."""
        drafts: List[Draft] = []
        raw_thread = result.get("thread", [])
        kind = "thread_draft" if full_draft else "thread_outline"
        
        # Thread-level algorithm metadata
        density_validated = result.get("density_validated", True)
        hook_strength = result.get("hook_strength", "moderate")
        suppression_risks = result.get("suppression_risks", [])

        for idx, item in enumerate(raw_thread):
            purpose = item.get("purpose", "body")
            density_score = item.get("density_score", "medium")
            unique_value = item.get("unique_value", "")
            
            draft = Draft(
                id=uuid4(),
                kind=kind,
                topic=topic,
                text=item.get("text", ""),
                tags=[purpose],
                spice=spice,
                persona_version=persona_version,
                rationale=result.get("rationale", ""),
                # Algorithm alignment fields
                hook_strength=hook_strength if idx == 0 else None,  # Only first tweet gets hook strength
                density_validated=density_validated,
                unique_value=unique_value,
                suppression_risk="low" if not suppression_risks else "medium",
                algorithm_alignment_notes=f"Density: {density_score}, Purpose: {purpose}",
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
        """Parse LLM reply result into Draft objects with algorithm metadata."""
        drafts: List[Draft] = []
        raw_replies = result.get("replies", [])

        for item in raw_replies:
            # Parse algorithm alignment fields
            suppression_risk = item.get("suppression_risk", "low")
            conversation_value = item.get("conversation_value", "medium")
            intent = item.get("intent", item.get("approach", "react"))
            value_added = item.get("value_added", "")
            
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
                # Algorithm alignment fields
                reply_intent=intent,
                suppression_risk=suppression_risk if suppression_risk in ["low", "medium", "high"] else "low",
                conversation_value=conversation_value if conversation_value in ["low", "medium", "high"] else "medium",
                unique_value=value_added,
                algorithm_alignment_notes=f"Intent: {intent}, Value: {value_added[:50] if value_added else 'N/A'}",
            )
            drafts.append(draft)

        return drafts
