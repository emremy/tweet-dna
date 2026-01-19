"""Import tweets from browser extension exports."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterator, List, Tuple

from tweetdna.storage import Repository


class ExtensionImportError(Exception):
    """Exception raised for extension import errors."""
    pass


class ExtensionImporter:
    """
    Import tweets from browser extension exports.
    
    Supports JSONL (one JSON object per line) and JSON (array of objects) formats.
    
    Expected schema per tweet:
    - tweet_id: string (required)
    - created_at: string ISO-8601 (required)
    - text: string (required)
    - url: string (required)
    - source: string (optional, defaults to 'extension_network')
    - metrics: object (optional)
    - lang: string (optional)
    - is_reply: boolean (optional)
    - is_quote: boolean (optional)
    - conversation_id: string (optional)
    """

    REQUIRED_FIELDS = {"tweet_id", "created_at", "text"}
    
    def __init__(self, repository: Repository):
        self.repository = repository

    def import_file(self, path: Path) -> Tuple[int, int, int]:
        """
        Import tweets from a file.
        
        Args:
            path: Path to JSONL or JSON file
            
        Returns:
            Tuple of (imported_count, skipped_invalid, deduped_count)
        """
        if not path.exists():
            raise ExtensionImportError(f"File not found: {path}")
        
        suffix = path.suffix.lower()
        
        if suffix == ".jsonl":
            tweets = list(self._read_jsonl(path))
        elif suffix == ".json":
            tweets = self._read_json(path)
        else:
            # Try JSONL first, then JSON
            try:
                tweets = list(self._read_jsonl(path))
            except json.JSONDecodeError:
                tweets = self._read_json(path)
        
        if not tweets:
            return 0, 0, 0
        
        return self.repository.import_extension_tweets_batch(tweets)

    def _read_jsonl(self, path: Path) -> Iterator[Dict[str, Any]]:
        """Read JSONL file (one JSON object per line)."""
        with open(path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    if isinstance(obj, dict):
                        yield self._normalize_tweet(obj)
                except json.JSONDecodeError as e:
                    raise ExtensionImportError(
                        f"Invalid JSON on line {line_num}: {e}"
                    )

    def _read_json(self, path: Path) -> List[Dict[str, Any]]:
        """Read JSON file (array of objects or single object)."""
        with open(path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError as e:
                raise ExtensionImportError(f"Invalid JSON file: {e}")
        
        if isinstance(data, list):
            return [self._normalize_tweet(obj) for obj in data if isinstance(obj, dict)]
        elif isinstance(data, dict):
            # Single object or wrapped format
            if "tweets" in data:
                return [self._normalize_tweet(obj) for obj in data["tweets"] if isinstance(obj, dict)]
            else:
                return [self._normalize_tweet(data)]
        else:
            raise ExtensionImportError("JSON must be an array or object")

    def _normalize_tweet(self, obj: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize tweet object to internal format.
        
        Handles various field name variations from extension exports.
        """
        # Handle ID field variations
        tweet_id = (
            obj.get("tweet_id") or
            obj.get("id") or
            obj.get("id_str") or
            obj.get("tweetId")
        )
        
        # Handle timestamp field variations
        created_at = (
            obj.get("created_at") or
            obj.get("createdAt") or
            obj.get("timestamp") or
            obj.get("date")
        )
        
        # Handle text field variations
        text = (
            obj.get("text") or
            obj.get("full_text") or
            obj.get("content") or
            ""
        )
        
        # Handle URL field variations
        url = (
            obj.get("url") or
            obj.get("tweet_url") or
            obj.get("link") or
            obj.get("permalink")
        )
        
        # Handle metrics
        metrics = obj.get("metrics")
        if not metrics and "public_metrics" in obj:
            metrics = obj["public_metrics"]
        elif not metrics:
            # Try to extract individual metric fields
            metrics = {}
            for key in ["like", "likes", "like_count", "favorite_count"]:
                if key in obj:
                    metrics["like"] = obj[key]
                    break
            for key in ["retweet", "retweets", "retweet_count"]:
                if key in obj:
                    metrics["retweet"] = obj[key]
                    break
            for key in ["reply", "replies", "reply_count"]:
                if key in obj:
                    metrics["reply"] = obj[key]
                    break
            for key in ["view", "views", "impression_count", "impressions"]:
                if key in obj:
                    metrics["view"] = obj[key]
                    break
            for key in ["quote", "quotes", "quote_count"]:
                if key in obj:
                    metrics["quote"] = obj[key]
                    break
            
            if not metrics:
                metrics = None
        
        return {
            "tweet_id": str(tweet_id) if tweet_id else None,
            "created_at": created_at,
            "text": text.strip() if text else None,
            "url": url,
            "source": obj.get("source", "extension_network"),
            "lang": obj.get("lang") or obj.get("language"),
            "metrics": metrics,
            "is_reply": obj.get("is_reply") or obj.get("isReply"),
            "is_quote": obj.get("is_quote") or obj.get("isQuote"),
            "conversation_id": obj.get("conversation_id") or obj.get("conversationId"),
        }

    def validate_file(self, path: Path) -> Tuple[bool, str]:
        """
        Validate an export file without importing.
        
        Returns (is_valid, message).
        """
        try:
            if not path.exists():
                return False, f"File not found: {path}"
            
            suffix = path.suffix.lower()
            count = 0
            valid_count = 0
            
            if suffix == ".jsonl":
                for tweet in self._read_jsonl(path):
                    count += 1
                    if self._is_valid_tweet(tweet):
                        valid_count += 1
            else:
                tweets = self._read_json(path)
                count = len(tweets)
                valid_count = sum(1 for t in tweets if self._is_valid_tweet(t))
            
            if count == 0:
                return False, "File contains no tweets"
            
            if valid_count == 0:
                return False, f"Found {count} records but none have required fields"
            
            return True, f"Valid: {valid_count}/{count} tweets have required fields"
            
        except ExtensionImportError as e:
            return False, str(e)
        except Exception as e:
            return False, f"Error reading file: {e}"

    def _is_valid_tweet(self, tweet: Dict[str, Any]) -> bool:
        """Check if tweet has all required fields."""
        return all(tweet.get(field) for field in ["tweet_id", "created_at", "text"])
