"""Cache factory for finwin."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from finwin.cache.base import BaseCache
from finwin.cache.memory import InMemoryCache
from finwin.cache.file import FileCache

if TYPE_CHECKING:
    from finwin.config.settings import CacheConfig


# Global cache instance (singleton)
_cache_instance: Optional[BaseCache] = None


def get_cache(
    cache_type: Optional[str] = None,
    config: Optional["CacheConfig"] = None,
) -> BaseCache:
    """
    Get or create a cache instance.
    
    Uses singleton pattern - returns same instance on subsequent calls.
    
    Args:
        cache_type: "memory" | "file" (overrides config)
        config: CacheConfig from settings
        
    Returns:
        Cache instance
    """
    global _cache_instance
    
    if _cache_instance is not None:
        return _cache_instance
    
    # Determine cache type
    if cache_type is None:
        if config is not None:
            cache_type = config.type
        else:
            cache_type = "file"  # Default to file cache
    
    # Get settings from config or use defaults
    if config is not None:
        default_ttl = config.default_ttl
        cache_dir = config.directory
    else:
        default_ttl = 86400  # 24 hours
        cache_dir = ".cache"
    
    # Create cache instance
    if cache_type == "memory":
        _cache_instance = InMemoryCache(default_ttl=default_ttl)
    elif cache_type == "file":
        _cache_instance = FileCache(
            cache_dir=cache_dir,
            default_ttl=default_ttl,
        )
    else:
        # Default to file cache for unknown types
        _cache_instance = FileCache(
            cache_dir=cache_dir,
            default_ttl=default_ttl,
        )
    
    return _cache_instance


def reset_cache() -> None:
    """Reset the cache singleton (useful for testing)."""
    global _cache_instance
    _cache_instance = None


def create_cache(
    cache_type: str = "file",
    **kwargs,
) -> BaseCache:
    """
    Create a new cache instance (non-singleton).
    
    Useful when you need multiple independent caches.
    
    Args:
        cache_type: "memory" | "file"
        **kwargs: Arguments passed to cache constructor
        
    Returns:
        New cache instance
    """
    if cache_type == "memory":
        return InMemoryCache(**kwargs)
    elif cache_type == "file":
        return FileCache(**kwargs)
    else:
        return FileCache(**kwargs)
