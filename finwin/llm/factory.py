"""LLM factory for creating provider instances."""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any, Dict, Optional, Type

from finwin.config.settings import get_settings
from finwin.llm.base import BaseLLM

logger = logging.getLogger(__name__)

# Registry of LLM providers
_LLM_PROVIDERS: Dict[str, Type[BaseLLM]] = {}


def register_llm(name: str):
    """Decorator to register an LLM provider."""
    def decorator(cls: Type[BaseLLM]) -> Type[BaseLLM]:
        _LLM_PROVIDERS[name] = cls
        return cls
    return decorator


def create_llm(
    provider: Optional[str] = None,
    model: Optional[str] = None,
    **kwargs: Any,
) -> BaseLLM:
    """
    Create an LLM instance.
    
    Uses settings for defaults if not specified.
    
    Args:
        provider: Provider name (bedrock, openai, anthropic, ollama)
        model: Model identifier
        **kwargs: Additional provider-specific arguments
        
    Returns:
        BaseLLM instance
        
    Raises:
        ValueError: If provider is not supported
    """
    settings = get_settings()
    
    provider = provider or settings.llm.provider
    model = model or settings.llm.model
    
    # Merge kwargs with settings
    final_kwargs = {
        "temperature": settings.llm.temperature,
        "max_tokens": settings.llm.max_tokens,
        **kwargs,
    }
    
    # Get provider class
    if provider not in _LLM_PROVIDERS:
        # Try to lazily import the provider
        _lazy_load_provider(provider)
    
    if provider not in _LLM_PROVIDERS:
        available = list(_LLM_PROVIDERS.keys())
        raise ValueError(
            f"Unknown LLM provider: {provider}. "
            f"Available: {available}. "
            "Make sure the provider package is installed."
        )
    
    provider_class = _LLM_PROVIDERS[provider]
    return provider_class(model=model, **final_kwargs)


def _lazy_load_provider(provider: str) -> None:
    """
    Lazily load a provider module.
    
    This allows providers to be optional dependencies.
    """
    try:
        if provider == "bedrock":
            from finwin.llm.providers import bedrock  # noqa: F401
        elif provider == "openai":
            from finwin.llm.providers import openai  # noqa: F401
        elif provider == "anthropic":
            from finwin.llm.providers import anthropic  # noqa: F401
        elif provider == "ollama":
            from finwin.llm.providers import ollama  # noqa: F401
    except ImportError as e:
        logger.warning(f"Failed to load LLM provider {provider}: {e}")


@lru_cache
def get_llm() -> BaseLLM:
    """
    Get cached LLM instance using default settings.
    
    Uses lru_cache for singleton pattern.
    Call get_llm.cache_clear() to reset.
    
    Returns:
        BaseLLM instance
    """
    return create_llm()


# Stub implementations for common providers
# These can be replaced with real implementations

@register_llm("stub")
class StubLLM(BaseLLM):
    """Stub LLM for testing."""
    
    provider_name = "stub"
    
    async def complete(self, messages, tools=None, **kwargs):
        from finwin.llm.base import LLMResponse
        return LLMResponse(
            content="This is a stub response for testing.",
            finish_reason="stop",
        )
