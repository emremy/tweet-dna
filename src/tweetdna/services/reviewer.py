"""Reviewer service for scoring and refining drafts."""

from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from tweetdna.prompts import build_review_prompt
from tweetdna.providers.base import LLMProvider
from tweetdna.schemas import Draft, Persona, ReviewResult
from tweetdna.storage import Repository


class ReviewerService:
    """
    Service for reviewing drafts against the persona.
    
    Scores persona alignment and optionally refines drafts.
    """

    def __init__(self, repository: Repository, provider: LLMProvider):
        self.repository = repository
        self.provider = provider

    def review_drafts(
        self,
        last_n: int = 10,
        auto_refine: bool = False,
    ) -> List[ReviewResult]:
        """
        Review recent drafts against the persona.
        
        Args:
            last_n: Number of recent drafts to review
            auto_refine: Whether to generate revised versions for low scores
            
        Returns:
            List of ReviewResult objects
        """
        persona = self._get_required_persona()
        drafts = self.repository.get_recent_generations(limit=last_n)

        if not drafts:
            return []

        results: List[ReviewResult] = []
        for draft in drafts:
            result = self._review_single(
                persona=persona,
                draft=draft,
                auto_refine=auto_refine,
            )
            results.append(result)

            # Save review to database
            self.repository.save_review(result)

        return results

    def review_single_draft(
        self,
        draft_id: str,
        auto_refine: bool = False,
    ) -> Optional[ReviewResult]:
        """Review a specific draft by ID."""
        persona = self._get_required_persona()
        draft = self.repository.get_generation_by_id(draft_id)

        if not draft:
            return None

        result = self._review_single(
            persona=persona,
            draft=draft,
            auto_refine=auto_refine,
        )

        self.repository.save_review(result)
        return result

    def _get_required_persona(self) -> Persona:
        """Get persona or raise error if not available."""
        persona = self.repository.get_latest_persona()
        if not persona:
            raise ValueError("No persona found. Run 'tweetdna profile' first.")
        return persona

    def _review_single(
        self,
        persona: Persona,
        draft: Draft,
        auto_refine: bool,
    ) -> ReviewResult:
        """Review a single draft."""
        # Get the text to review
        text = draft.text if isinstance(draft.text, str) else "\n".join(draft.text)

        prompt = build_review_prompt(
            persona=persona,
            draft_text=text,
            auto_refine=auto_refine,
        )

        result = self.provider.generate_json(
            prompt=prompt,
            schema={"type": "object"},
            temperature=0.3,  # Lower temperature for consistent scoring
        )

        return ReviewResult(
            draft_id=draft.id,
            alignment_score=result.get("alignment_score", 0),
            violations=result.get("violations", []),
            suggestions=result.get("suggestions", []),
            revised_text=result.get("revised_text"),
        )
