"""HTML text extractor for finwin."""

from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Tuple

import trafilatura
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=4)


def _extract_sync(html: str, url: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
    """
    Synchronous HTML text extraction.
    
    Uses trafilatura first, falls back to BeautifulSoup.
    """
    try:
        # Try trafilatura first (better at extracting article content)
        extracted = trafilatura.extract(
            html,
            include_comments=False,
            include_tables=True,
            url=url,
        )
        
        if extracted:
            return extracted, None
        
        # Fallback to BeautifulSoup plain text
        soup = BeautifulSoup(html, "html.parser")
        
        # Remove script and style elements
        for element in soup(["script", "style", "nav", "footer", "header"]):
            element.decompose()
        
        text = soup.get_text("\n", strip=True)
        
        if text:
            return text, None
        
        return None, "No text extracted"
        
    except Exception as e:
        logger.warning(f"HTML extraction failed: {e}")
        return None, str(e)


class HTMLExtractor:
    """Extracts text from HTML content."""
    
    async def extract(
        self,
        html: str,
        url: Optional[str] = None,
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract text from HTML.
        
        Args:
            html: HTML content
            url: Source URL (helps trafilatura)
            
        Returns:
            Tuple of (extracted_text, error)
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            _executor,
            _extract_sync,
            html,
            url,
        )
