"""Configuration management for TweetDNA."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal, Optional

from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()


class Config(BaseModel):
    """Application configuration loaded from environment variables."""

    # Core paths
    db_path: Path = Path(os.getenv("TWEETDNA_DB_PATH", "./data/tweetdna.sqlite"))
    cache_dir: Path = Path(os.getenv("TWEETDNA_CACHE_DIR", "./data/cache"))
    log_level: str = os.getenv("TWEETDNA_LOG_LEVEL", "INFO")

    # LLM provider settings
    llm_provider: Literal["openai", "local"] = os.getenv("LLM_PROVIDER", "openai")  # type: ignore
    llm_model_profile: str = os.getenv("LLM_MODEL_PROFILE", "gpt-4o")
    llm_model_generate: str = os.getenv("LLM_MODEL_GENERATE", "gpt-4o-mini")
    llm_model_review: str = os.getenv("LLM_MODEL_REVIEW", "gpt-4o-mini")

    # OpenAI
    openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY")

    # Local LLM (Ollama)
    local_llm_base_url: str = os.getenv("LOCAL_LLM_BASE_URL", "http://127.0.0.1:11434")
    local_llm_model: str = os.getenv("LOCAL_LLM_MODEL", "llama3")

    # Embeddings (optional, for better example retrieval)
    embeddings_provider: Literal["openai", "local", "none"] = os.getenv(  # type: ignore
        "EMBEDDINGS_PROVIDER", "none"
    )
    embeddings_model: Optional[str] = os.getenv("EMBEDDINGS_MODEL")


def get_config() -> Config:
    """Get the application configuration."""
    return Config()
