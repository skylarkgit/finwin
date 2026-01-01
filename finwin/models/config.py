"""Configuration models for finwin."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class CollectorConfig(BaseModel):
    """Configuration for the ContextCollector."""
    
    # HTTP settings
    timeout: int = 25
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/132.0.0.0 Safari/537.36"
    )
    
    # Rate limiting
    sleep_between_requests: float = 1.0
    max_concurrent_requests: int = 5
    
    # News settings
    news_country: str = "IN"
    news_language: str = "en"
    default_news_items: int = 10
    
    # Cache settings
    cache_ttl: int = 300  # 5 minutes
    enable_cache: bool = True
