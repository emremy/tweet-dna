"""Reviewer service for scoring and refining drafts."""

from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from tweetdna.prompts import build_review_prompt
from tweetdna.providers.base import LLMProvider
from tweetdna.schemas import Draft, Persona, PersonaAlgorithmConflict, ReviewResult
from tweetdna.storage import Repository


class ReviewerService:
    """
    Service for reviewing drafts against the persona AND algorithm alignment.
    
    Algorithm-aware features:
    - Scores both persona alignment and algorithm alignment
    - Detects suppression risk patterns
    - Assesses conversation value and repetition risk
    - Resolves conflicts between persona style and algorithm constraints
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
        Review recent drafts against persona AND algorithm constraints.
        
        Args:
            last_n: Number of recent drafts to review
            auto_refine: Whether to generate revised versions for:
                - Low alignment scores (< 80)
                - High suppression risk (> 50)
            
        Returns:
            List of ReviewResult objects with algorithm metadata
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
        """Review a specific draft by ID with algorithm alignment scoring."""
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

    def _determine_draft_kind(self, draft: Draft) -> str:
        """Determine the kind of draft for appropriate review criteria."""
        if draft.kind == "reply":
            return "reply"
        elif draft.kind in ["thread_outline", "thread_draft"]:
            return "thread"
        else:
            return "tweet"

    def _review_single(
        self,
        persona: Persona,
        draft: Draft,
        auto_refine: bool,
    ) -> ReviewResult:
        """Review a single draft with algorithm alignment scoring."""
        # Get the text to review
        text = draft.text if isinstance(draft.text, str) else "\n".join(draft.text)
        
        # Determine draft kind for appropriate review criteria
        draft_kind = self._determine_draft_kind(draft)

        # Build prompt with algorithm-aware review
        prompt = build_review_prompt(
            persona=persona,
            draft_text=text,
            auto_refine=auto_refine,
            draft_kind=draft_kind,
        )

        result = self.provider.generate_json(
            prompt=prompt,
            schema={"type": "object"},
            temperature=0.3,  # Lower temperature for consistent scoring
        )

        # Parse persona-algorithm conflicts
        raw_conflicts = result.get("persona_algorithm_conflicts", [])
        conflicts = []
        for conflict in raw_conflicts:
            if isinstance(conflict, dict):
                conflicts.append(PersonaAlgorithmConflict(
                    persona_rule=conflict.get("persona_rule", ""),
                    algorithm_constraint=conflict.get("algorithm_constraint", ""),
                    resolution=conflict.get("resolution", ""),
                ))

        # Parse risk levels with validation
        repetition_risk = result.get("repetition_risk")
        if repetition_risk not in ["low", "medium", "high"]:
            repetition_risk = "low"
        
        conversation_value = result.get("conversation_value")
        if conversation_value not in ["low", "medium", "high"]:
            conversation_value = "medium"

        return ReviewResult(
            draft_id=draft.id,
            alignment_score=result.get("alignment_score", 0),
            violations=result.get("violations", []),
            suggestions=result.get("suggestions", []),
            revised_text=result.get("revised_text"),
            # Algorithm alignment fields
            algorithm_alignment_score=result.get("algorithm_alignment_score"),
            suppression_risk_score=result.get("suppression_risk_score"),
            repetition_risk=repetition_risk,
            conversation_value=conversation_value,
            algorithm_issues=result.get("algorithm_issues", []),
            persona_algorithm_conflicts=conflicts,
            revision_reason=result.get("revision_reason"),
        )
    
    def check_suppression_risk(self, text: str) -> dict:
        """
        Quick check for common suppression risk patterns.
        
        Returns dict with risk level and detected patterns.
        This is a deterministic check that doesn't require LLM calls.
        """
        patterns_found = []
        text_lower = text.lower().strip()
        
        # Engagement bait patterns
        engagement_bait = [
            "like if", "rt if", "retweet if", "follow for follow",
            "f4f", "like for like", "l4l", "follow back",
        ]
        for pattern in engagement_bait:
            if pattern in text_lower:
                patterns_found.append(f"engagement_bait:{pattern}")
        
        # Question patterns (shadowban risk)
        question_patterns = [
            "what do you think",
            "anyone else",
            "am i the only one",
            "thoughts?",
            "agree or disagree",
            "right?",
            "don't you think",
            "isn't it",
            "wouldn't you",
            "who else",
        ]
        for pattern in question_patterns:
            if pattern in text_lower:
                patterns_found.append(f"question_pattern:{pattern}")
        
        # Opinion-labeling openers (banned - cause repetitive content)
        opinion_labels = [
            "unpopular opinion",
            "hot take",
            "controversial take",
            "just saying",
            "hear me out",
            "most people miss this",
            "most people don't realize",
            "most people won't tell you",
            "most people forget",
            "most people overlook",
            "i'll probably get hate for this",
            "not sure if this is controversial",
            "this might be a hot take",
            "everyone's wrong about",
        ]
        for pattern in opinion_labels:
            if text_lower.startswith(pattern) or f" {pattern}" in text_lower[:50]:
                patterns_found.append(f"opinion_label:{pattern}")
        
        # Check if tweet ends with a question mark (high risk)
        if text.rstrip().endswith("?"):
            patterns_found.append("ends_with_question")
        
        # Count total question marks (multiple = high risk)
        question_count = text.count("?")
        if question_count > 1:
            patterns_found.append(f"multiple_questions:{question_count}")
        
        # Excessive hashtags
        hashtag_count = text.count("#")
        if hashtag_count > 3:
            patterns_found.append(f"excessive_hashtags:{hashtag_count}")
        
        # Excessive mentions
        mention_count = text.count("@")
        if mention_count > 3:
            patterns_found.append(f"excessive_mentions:{mention_count}")
        
        # Low effort patterns
        low_effort = ["this", "same", "facts", "real", "💯", "🔥", "👏"]
        if text_lower in low_effort or text.strip() in low_effort:
            patterns_found.append("low_effort_content")
        
        # Determine risk level
        # Questions are weighted more heavily due to shadowban risk
        question_issues = [p for p in patterns_found if "question" in p]
        other_issues = [p for p in patterns_found if "question" not in p]
        
        if len(question_issues) > 0:
            # Any question pattern is at least medium risk
            if len(question_issues) > 1 or len(other_issues) > 0:
                risk_level = "high"
            else:
                risk_level = "medium"
        elif len(other_issues) == 0:
            risk_level = "low"
        elif len(other_issues) <= 2:
            risk_level = "medium"
        else:
            risk_level = "high"
        
        return {
            "risk_level": risk_level,
            "patterns_found": patterns_found,
            "recommendation": "review" if risk_level != "low" else "ok",
        }