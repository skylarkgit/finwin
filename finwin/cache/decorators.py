"""Cache decorators for finwin."""

from __future__ import annotations

import functools
import hashlib
import json
from typing import Any, Callable, Optional, TypeVar, Union

from finwin.cache.base import BaseCache

F = TypeVar("F", bound=Callable[..., Any])


def make_cache_key(*args, **kwargs) -> str:
    """
    Create a cache key from function arguments.
    
    Handles various types including dicts, lists, and primitives.
    """
    key_parts = []
    
    for arg in args:
        if isinstance(arg, (str, int, float, bool, type(None))):
            key_parts.append(str(arg))
        elif isinstance(arg, (list, tuple)):
            key_parts.append(json.dumps(arg, sort_keys=True, default=str))
        elif isinstance(arg, dict):
            key_parts.append(json.dumps(arg, sort_keys=True, default=str))
        else:
            # For objects, use repr or class name
            key_parts.append(repr(arg))
    
    for key, value in sorted(kwargs.items()):
        if isinstance(value, (str, int, float, bool, type(None))):
            key_parts.append(f"{key}={value}")
        elif isinstance(value, (list, tuple, dict)):
            key_parts.append(f"{key}={json.dumps(value, sort_keys=True, default=str)}")
        else:
            key_parts.append(f"{key}={repr(value)}")
    
    return ":".join(key_parts)


def cached(
    cache: Optional[BaseCache] = None,
    ttl: Optional[int] = None,
    key_prefix: Optional[str] = None,
    key_builder: Optional[Callable[..., str]] = None,
):
    """
    Decorator to cache async function results.
    
    Usage:
        @cached(ttl=3600)
        async def fetch_data(symbol: str) -> dict:
            ...
        
        # With custom key builder
        @cached(key_prefix="gdp", key_builder=lambda c, i: f"{c}:{i}")
        async def get_gdp(country: str, indicator: str) -> dict:
            ...
    
    Args:
        cache: Cache instance to use (defaults to global cache)
        ttl: Time-to-live in seconds (None = use cache default)
        key_prefix: Prefix for cache keys
        key_builder: Custom function to build cache key from args
    
    Returns:
        Decorated function
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            # Get cache instance
            nonlocal cache
            if cache is None:
                from finwin.cache.factory import get_cache
                cache = get_cache()
            
            # Build cache key
            if key_builder is not None:
                key_suffix = key_builder(*args, **kwargs)
            else:
                key_suffix = make_cache_key(*args, **kwargs)
            
            # Add function name and prefix
            func_name = func.__qualname__
            if key_prefix:
                cache_key = f"{key_prefix}:{func_name}:{key_suffix}"
            else:
                cache_key = f"{func_name}:{key_suffix}"
            
            # Try to get from cache
            cached_value = await cache.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # Call function and cache result
            result = await func(*args, **kwargs)
            
            # Only cache non-None results
            if result is not None:
                await cache.set(cache_key, result, ttl=ttl)
            
            return result
        
        # Store original function for testing
        wrapper.__wrapped__ = func
        return wrapper
    
    return decorator


def cached_method(
    ttl: Optional[int] = None,
    key_prefix: Optional[str] = None,
    cache_attr: str = "_cache",
):
    """
    Decorator for caching instance methods.
    
    Looks for cache on the instance (self._cache by default).
    
    Usage:
        class MyProvider:
            def __init__(self):
                self._cache = get_cache()
            
            @cached_method(ttl=3600)
            async def fetch(self, symbol: str) -> dict:
                ...
    
    Args:
        ttl: Time-to-live in seconds
        key_prefix: Prefix for cache keys
        cache_attr: Attribute name to find cache on self
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(self, *args, **kwargs) -> Any:
            # Get cache from instance
            cache = getattr(self, cache_attr, None)
            if cache is None:
                # Fallback to global cache
                from finwin.cache.factory import get_cache
                cache = get_cache()
            
            # Build cache key
            key_suffix = make_cache_key(*args, **kwargs)
            func_name = func.__qualname__
            
            if key_prefix:
                cache_key = f"{key_prefix}:{func_name}:{key_suffix}"
            else:
                cache_key = f"{func_name}:{key_suffix}"
            
            # Try to get from cache
            cached_value = await cache.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # Call function and cache result
            result = await func(self, *args, **kwargs)
            
            # Only cache non-None results
            if result is not None:
                await cache.set(cache_key, result, ttl=ttl)
            
            return result
        
        wrapper.__wrapped__ = func
        return wrapper
    
    return decorator
