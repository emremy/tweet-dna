"""Factory for creating LLM providers based on configuration."""

from tweetdna.config import Config
from tweetdna.providers.base import LLMProvider
from tweetdna.providers.local import LocalProvider
from tweetdna.providers.openai import OpenAIProvider


def get_provider(config: Config, role: str = "generate") -> LLMProvider:
    """
    Create an LLM provider based on configuration.
    
    Args:
        config: Application configuration
        role: One of "profile", "generate", or "review" to select the appropriate model
        
    Returns:
        Configured LLM provider instance
    """
    # Select model based on role
    model_map = {
        "profile": config.llm_model_profile,
        "generate": config.llm_model_generate,
        "review": config.llm_model_review,
    }
    model = model_map.get(role, config.llm_model_generate)

    if config.llm_provider == "openai":
        api_key = config.openai_api_key or "stub"
        return OpenAIProvider(api_key=api_key, default_model=model)

    elif config.llm_provider == "local":
        return LocalProvider(
            base_url=config.local_llm_base_url,
            default_model=config.local_llm_model,
        )

    # Default to OpenAI with stub key
    return OpenAIProvider(api_key="stub", default_model=model)
