"""Utility functions for finwin."""

from __future__ import annotations

import hashlib
import re


def slugify(s: str, max_length: int = 80) -> str:
    """
    Convert string to a safe slug.
    
    Args:
        s: Input string
        max_length: Maximum length of output
        
    Returns:
        Slugified string
    """
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")[:max_length] or "output"


def sha1_short(s: str, length: int = 12) -> str:
    """
    Generate a short SHA1 hash of a string.
    
    Args:
        s: Input string
        length: Length of output hash
        
    Returns:
        Truncated SHA1 hash
    """
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:length]
