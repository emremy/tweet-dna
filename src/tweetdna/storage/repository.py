"""Repository layer for database operations."""

from __future__ import annotations

import json
import random
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4

from tweetdna.schemas import Draft, Persona, ReviewResult
from tweetdna.storage.database import Database


class Repository:
    """Repository for all database operations."""

    def __init__(self, db: Database):
        self.db = db

    # --- Tweet operations (extension import) ---

    def import_extension_tweet(
        self,
        tweet_id: str,
        created_at: str,
        text: str,
        url: Optional[str] = None,
        source: str = "extension_network",
        lang: Optional[str] = None,
        metrics: Optional[Dict[str, Any]] = None,
        raw: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Import a single tweet from extension export.
        
        Returns True if inserted, False if already exists (dedupe).
        """
        conn = self.db.connect()
        cursor = conn.cursor()
        
        # Check if tweet already exists
        cursor.execute("SELECT 1 FROM tweets WHERE tweet_id = ?", (tweet_id,))
        if cursor.fetchone():
            return False  # Already exists
        
        cursor.execute(
            """
            INSERT INTO tweets (tweet_id, created_at, text, url, source, lang, metrics_json, raw_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                tweet_id,
                created_at,
                text,
                url,
                source,
                lang,
                json.dumps(metrics) if metrics else None,
                json.dumps(raw) if raw else None,
            ),
        )
        conn.commit()
        return True

    def import_extension_tweets_batch(
        self,
        tweets: List[Dict[str, Any]],
    ) -> Tuple[int, int, int]:
        """
        Import multiple tweets from extension export.
        
        Returns (imported_count, skipped_invalid, deduped_count).
        """
        conn = self.db.connect()
        cursor = conn.cursor()
        
        imported = 0
        skipped_invalid = 0
        deduped = 0
        
        for tweet in tweets:
            # Validate required fields
            tweet_id = tweet.get("tweet_id")
            created_at = tweet.get("created_at")
            text = tweet.get("text")
            
            if not tweet_id or not created_at or not text:
                skipped_invalid += 1
                continue
            
            # Check for duplicate
            cursor.execute("SELECT 1 FROM tweets WHERE tweet_id = ?", (tweet_id,))
            if cursor.fetchone():
                deduped += 1
                continue
            
            # Insert tweet
            cursor.execute(
                """
                INSERT INTO tweets (tweet_id, created_at, text, url, source, lang, metrics_json, raw_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    tweet_id,
                    created_at,
                    text,
                    tweet.get("url"),
                    tweet.get("source", "extension_network"),
                    tweet.get("lang"),
                    json.dumps(tweet.get("metrics")) if tweet.get("metrics") else None,
                    json.dumps(tweet) if tweet else None,
                ),
            )
            imported += 1
        
        conn.commit()
        return imported, skipped_invalid, deduped

    def get_tweet_count(self) -> int:
        """Get total number of tweets in database."""
        conn = self.db.connect()
        cursor = conn.execute("SELECT COUNT(*) FROM tweets")
        return cursor.fetchone()[0]

    def get_tweets(
        self,
        limit: int = 100,
        offset: int = 0,
        since: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get tweets with optional filtering."""
        conn = self.db.connect()
        query = "SELECT * FROM tweets"
        params: List[Any] = []

        if since:
            query += " WHERE created_at >= ?"
            params.append(since)

        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor = conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    def sample_tweets_for_profiling(self, sample_size: int = 300) -> List[Dict[str, Any]]:
        """
        Sample tweets for persona profiling.
        Uses stratified sampling across time to ensure diversity.
        
        This is the ONLY method that provides tweets for LLM consumption.
        """
        conn = self.db.connect()

        # Get total count
        total = self.get_tweet_count()
        if total == 0:
            return []

        if total <= sample_size:
            cursor = conn.execute("SELECT * FROM tweets ORDER BY created_at")
            return [dict(row) for row in cursor.fetchall()]

        # Stratified sampling: divide into time buckets and sample from each
        cursor = conn.execute(
            "SELECT tweet_id, created_at, text, url, source, lang, metrics_json, raw_json FROM tweets ORDER BY created_at"
        )
        all_tweets = [dict(row) for row in cursor.fetchall()]

        # Simple random sampling with time diversity
        # Take some from beginning, middle, and end to ensure temporal coverage
        chunk_size = len(all_tweets) // 3
        samples: List[Dict[str, Any]] = []

        for i in range(3):
            start = i * chunk_size
            end = start + chunk_size if i < 2 else len(all_tweets)
            chunk = all_tweets[start:end]
            chunk_sample_size = sample_size // 3
            if i == 2:
                chunk_sample_size = sample_size - len(samples)
            samples.extend(random.sample(chunk, min(chunk_sample_size, len(chunk))))

        return samples

    # --- Persona operations ---

    def save_persona(self, persona: Persona) -> int:
        """Save a new persona version. Returns the new version number."""
        conn = self.db.connect()
        cursor = conn.execute(
            "INSERT INTO persona_versions (persona_json) VALUES (?)",
            (persona.model_dump_json(),),
        )
        conn.commit()
        return cursor.lastrowid or 1

    def get_latest_persona(self) -> Optional[Persona]:
        """Get the most recent persona version."""
        conn = self.db.connect()
        cursor = conn.execute(
            "SELECT version, persona_json FROM persona_versions ORDER BY version DESC LIMIT 1"
        )
        row = cursor.fetchone()
        if row is None:
            return None
        persona_data = json.loads(row["persona_json"])
        persona_data["version"] = row["version"]
        return Persona.model_validate(persona_data)

    def get_persona_by_version(self, version: int) -> Optional[Persona]:
        """Get a specific persona version."""
        conn = self.db.connect()
        cursor = conn.execute(
            "SELECT version, persona_json FROM persona_versions WHERE version = ?",
            (version,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        persona_data = json.loads(row["persona_json"])
        persona_data["version"] = row["version"]
        return Persona.model_validate(persona_data)

    # --- Generation operations ---

    def save_generation(
        self,
        draft: Draft,
        provider: str,
        model: str,
        prompt_hash: str,
    ) -> str:
        """Save a generation to the database. Returns the generation ID."""
        conn = self.db.connect()
        gen_id = str(draft.id)
        text_json = json.dumps(draft.text if isinstance(draft.text, list) else [draft.text])
        tags_json = json.dumps(draft.tags)

        conn.execute(
            """
            INSERT INTO generations 
            (id, kind, topic, spice, persona_version, text_json, tags_json, rationale, confidence, provider, model, prompt_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                gen_id,
                draft.kind,
                draft.topic,
                draft.spice,
                draft.persona_version,
                text_json,
                tags_json,
                draft.rationale,
                draft.confidence,
                provider,
                model,
                prompt_hash,
            ),
        )
        conn.commit()
        return gen_id

    def get_recent_generations(self, limit: int = 10) -> List[Draft]:
        """Get the most recent generations."""
        conn = self.db.connect()
        cursor = conn.execute(
            """
            SELECT id, kind, topic, spice, persona_version, text_json, tags_json, rationale, confidence
            FROM generations ORDER BY created_at DESC LIMIT ?
            """,
            (limit,),
        )
        drafts: List[Draft] = []
        for row in cursor.fetchall():
            text_data = json.loads(row["text_json"])
            text = text_data[0] if len(text_data) == 1 else text_data
            drafts.append(
                Draft(
                    id=UUID(row["id"]),
                    kind=row["kind"],
                    topic=row["topic"],
                    spice=row["spice"],
                    persona_version=row["persona_version"],
                    text=text,
                    tags=json.loads(row["tags_json"]) if row["tags_json"] else [],
                    rationale=row["rationale"] or "",
                    confidence=row["confidence"] or 0.8,
                )
            )
        return drafts

    def get_generation_by_id(self, gen_id: str) -> Optional[Draft]:
        """Get a generation by its ID."""
        conn = self.db.connect()
        cursor = conn.execute(
            """
            SELECT id, kind, topic, spice, persona_version, text_json, tags_json, rationale, confidence
            FROM generations WHERE id = ?
            """,
            (gen_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        text_data = json.loads(row["text_json"])
        text = text_data[0] if len(text_data) == 1 else text_data
        return Draft(
            id=UUID(row["id"]),
            kind=row["kind"],
            topic=row["topic"],
            spice=row["spice"],
            persona_version=row["persona_version"],
            text=text,
            tags=json.loads(row["tags_json"]) if row["tags_json"] else [],
            rationale=row["rationale"] or "",
            confidence=row["confidence"] or 0.8,
        )

    # --- Review operations ---

    def save_review(self, review: ReviewResult) -> str:
        """Save a review result. Returns the review ID."""
        conn = self.db.connect()
        review_id = str(uuid4())
        conn.execute(
            """
            INSERT INTO reviews (id, generation_id, alignment_score, violations_json, suggestions_json, revised_text_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                review_id,
                str(review.draft_id),
                review.alignment_score,
                json.dumps(review.violations),
                json.dumps(review.suggestions),
                json.dumps(review.revised_text) if review.revised_text else None,
            ),
        )
        conn.commit()
        return review_id

    def get_reviews_for_generation(self, generation_id: str) -> List[ReviewResult]:
        """Get all reviews for a generation."""
        conn = self.db.connect()
        cursor = conn.execute(
            """
            SELECT generation_id, alignment_score, violations_json, suggestions_json, revised_text_json
            FROM reviews WHERE generation_id = ? ORDER BY created_at DESC
            """,
            (generation_id,),
        )
        reviews: List[ReviewResult] = []
        for row in cursor.fetchall():
            revised = json.loads(row["revised_text_json"]) if row["revised_text_json"] else None
            reviews.append(
                ReviewResult(
                    draft_id=UUID(row["generation_id"]),
                    alignment_score=row["alignment_score"],
                    violations=json.loads(row["violations_json"]) if row["violations_json"] else [],
                    suggestions=json.loads(row["suggestions_json"]) if row["suggestions_json"] else [],
                    revised_text=revised,
                )
            )
        return reviews
