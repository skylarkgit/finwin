"""Generic web fetcher for finwin."""

from __future__ import annotations

import logging
from typing import Any, List, Optional

import httpx

from finwin.extractors import HTMLExtractor, PDFExtractor
from finwin.models.context import FetchResult, SourceResult
from finwin.sources.base import BaseSource, register_source

logger = logging.getLogger(__name__)


@register_source("web")
class WebFetcher(BaseSource):
    """
    Fetches and extracts text from arbitrary URLs.
    
    Supports HTML pages and PDF documents.
    """
    
    name = "web"
    
    def __init__(
        self,
        timeout: int = 25,
        user_agent: str = (
            "Mozilla/5.0 (X11; Linux x86_64) "
            "StockContextCollector/1.0"
        ),
    ):
        self.timeout = timeout
        self.user_agent = user_agent
        self._client: Optional[httpx.AsyncClient] = None
        self._html_extractor = HTMLExtractor()
        self._pdf_extractor = PDFExtractor()
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True,
            )
        return self._client
    
    async def close(self) -> None:
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def fetch_url(self, url: str) -> FetchResult:
        """
        Fetch a single URL and extract text.
        
        Args:
            url: URL to fetch
            
        Returns:
            FetchResult with extracted text
        """
        client = await self._get_client()
        
        headers = {
            "User-Agent": self.user_agent,
            "Accept-Language": "en-IN,en;q=0.9",
        }
        
        try:
            r = await client.get(url, headers=headers)
            ct = r.headers.get("Content-Type", "")
            status = r.status_code
            
            extracted_text = None
            error = None
            
            if 200 <= status < 300:
                # Determine content type and extract
                if "pdf" in ct.lower() or url.lower().endswith(".pdf"):
                    extracted_text, error = await self._pdf_extractor.extract(
                        r.content
                    )
                else:
                    extracted_text, error = await self._html_extractor.extract(
                        r.text, url
                    )
            
            return FetchResult(
                url=url,
                resolved_url=str(r.url) if str(r.url) != url else None,
                status=status,
                content_type=ct,
                extracted_text=extracted_text,
                error=error,
            )
            
        except Exception as e:
            logger.warning(f"Failed to fetch {url}: {e}")
            return FetchResult(
                url=url,
                status=-1,
                content_type="",
                error=str(e),
            )
    
    async def gather(
        self,
        symbol: Optional[str] = None,
        query: Optional[str] = None,
        **kwargs: Any,
    ) -> SourceResult:
        """
        Fetch URLs and extract text.
        
        Args:
            symbol: Not used
            query: Not used
            **kwargs: Must include 'urls' list
            
        Returns:
            SourceResult with fetch results
        """
        urls: List[str] = kwargs.get("urls", [])
        
        if not urls:
            return SourceResult(
                name=self.name,
                success=True,
                data={"fetches": [], "count": 0},
                raw_texts=[],
            )
        
        fetches: List[FetchResult] = []
        raw_texts: List[str] = []
        
        for url in urls:
            result = await self.fetch_url(url)
            fetches.append(result)
            
            if result.extracted_text:
                raw_texts.append(result.extracted_text)
        
        return SourceResult(
            name=self.name,
            success=True,
            data={
                "fetches": [f.model_dump() for f in fetches],
                "count": len(fetches),
            },
            raw_texts=raw_texts,
        )
