"""In-memory cache implementation for finwin."""

from __future__ import annotations

import time
from typing import Any, Dict, Optional, Tuple

from finwin.cache.base import BaseCache


class InMemoryCache(BaseCache):
    """
    Simple in-memory cache with TTL support.
    
    Suitable for single-process applications.
    """
    
    def __init__(self, default_ttl: int = 300):
        """
        Initialize cache.
        
        Args:
            default_ttl: Default time-to-live in seconds (default: 5 minutes)
        """
        self.default_ttl = default_ttl
        self._cache: Dict[str, Tuple[Any, float]] = {}  # key -> (value, expiry)
    
    async def get(self, key: str) -> Optional[Any]:
        """Get a value from cache."""
        if key not in self._cache:
            return None
        
        value, expiry = self._cache[key]
        
        if time.time() > expiry:
            # Expired
            del self._cache[key]
            return None
        
        return value
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> None:
        """Set a value in cache."""
        actual_ttl = ttl if ttl is not None else self.default_ttl
        expiry = time.time() + actual_ttl
        self._cache[key] = (value, expiry)
    
    async def delete(self, key: str) -> None:
        """Delete a key from cache."""
        self._cache.pop(key, None)
    
    async def clear(self) -> None:
        """Clear all cached values."""
        self._cache.clear()
    
    async def cleanup_expired(self) -> int:
        """
        Remove all expired entries.
        
        Returns:
            Number of entries removed
        """
        now = time.time()
        expired_keys = [
            k for k, (_, expiry) in self._cache.items()
            if now > expiry
        ]
        
        for key in expired_keys:
            del self._cache[key]
        
        return len(expired_keys)
