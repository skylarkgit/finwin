"""File-based cache implementation for finwin."""

from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any, Optional

from finwin.cache.base import BaseCache


class FileCache(BaseCache):
    """
    File-based cache with TTL support.
    
    Persists data to disk as JSON files.
    Survives server restarts.
    
    Cache structure:
        {cache_dir}/
            {key_hash}.json  →  {"data": ..., "expires": timestamp, "key": original_key}
    """
    
    def __init__(
        self,
        cache_dir: str = ".cache",
        default_ttl: int = 86400,  # 24 hours
    ):
        """
        Initialize file cache.
        
        Args:
            cache_dir: Directory to store cache files
            default_ttl: Default time-to-live in seconds
        """
        self.cache_dir = Path(cache_dir)
        self.default_ttl = default_ttl
        self._ensure_cache_dir()
    
    def _ensure_cache_dir(self) -> None:
        """Create cache directory if it doesn't exist."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def _key_to_filename(self, key: str) -> Path:
        """Convert cache key to safe filename."""
        # Use a simple hash-based filename to avoid filesystem issues
        import hashlib
        key_hash = hashlib.sha256(key.encode()).hexdigest()[:32]
        return self.cache_dir / f"{key_hash}.json"
    
    def _read_cache_file(self, filepath: Path) -> Optional[dict]:
        """Read and parse a cache file."""
        try:
            if not filepath.exists():
                return None
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError, OSError):
            # Corrupted or unreadable file
            return None
    
    def _write_cache_file(self, filepath: Path, data: dict) -> bool:
        """
        Write data to cache file atomically.
        
        Uses write-to-temp-then-rename pattern for atomic writes.
        """
        try:
            self._ensure_cache_dir()
            
            # Write to temp file first
            fd, temp_path = tempfile.mkstemp(
                dir=self.cache_dir,
                suffix=".tmp",
            )
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(data, f, default=str, indent=2)
                
                # Atomic rename
                os.replace(temp_path, filepath)
                return True
            except Exception:
                # Clean up temp file on failure
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                raise
        except (IOError, OSError) as e:
            # Log error in production
            return False
    
    async def get(self, key: str) -> Optional[Any]:
        """Get a value from cache."""
        filepath = self._key_to_filename(key)
        cache_entry = self._read_cache_file(filepath)
        
        if cache_entry is None:
            return None
        
        # Check expiration
        expires = cache_entry.get("expires", 0)
        if time.time() > expires:
            # Expired - delete file
            try:
                filepath.unlink()
            except OSError:
                pass
            return None
        
        return cache_entry.get("data")
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> None:
        """Set a value in cache."""
        actual_ttl = ttl if ttl is not None else self.default_ttl
        expires = time.time() + actual_ttl
        
        cache_entry = {
            "key": key,
            "data": value,
            "expires": expires,
            "created": time.time(),
            "ttl": actual_ttl,
        }
        
        filepath = self._key_to_filename(key)
        self._write_cache_file(filepath, cache_entry)
    
    async def delete(self, key: str) -> None:
        """Delete a key from cache."""
        filepath = self._key_to_filename(key)
        try:
            filepath.unlink()
        except OSError:
            pass
    
    async def clear(self) -> None:
        """Clear all cached values."""
        try:
            for filepath in self.cache_dir.glob("*.json"):
                try:
                    filepath.unlink()
                except OSError:
                    pass
        except OSError:
            pass
    
    async def cleanup_expired(self) -> int:
        """
        Remove all expired entries.
        
        Returns:
            Number of entries removed
        """
        removed = 0
        now = time.time()
        
        try:
            for filepath in self.cache_dir.glob("*.json"):
                cache_entry = self._read_cache_file(filepath)
                if cache_entry is None:
                    continue
                
                expires = cache_entry.get("expires", 0)
                if now > expires:
                    try:
                        filepath.unlink()
                        removed += 1
                    except OSError:
                        pass
        except OSError:
            pass
        
        return removed
    
    async def get_stats(self) -> dict:
        """
        Get cache statistics.
        
        Returns:
            Dict with count, size, expired counts
        """
        stats = {
            "total_files": 0,
            "total_size_bytes": 0,
            "expired_count": 0,
            "valid_count": 0,
        }
        
        now = time.time()
        
        try:
            for filepath in self.cache_dir.glob("*.json"):
                stats["total_files"] += 1
                stats["total_size_bytes"] += filepath.stat().st_size
                
                cache_entry = self._read_cache_file(filepath)
                if cache_entry:
                    expires = cache_entry.get("expires", 0)
                    if now > expires:
                        stats["expired_count"] += 1
                    else:
                        stats["valid_count"] += 1
        except OSError:
            pass
        
        return stats
