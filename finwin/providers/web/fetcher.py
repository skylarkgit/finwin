"""Generic web fetcher provider for finwin."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import httpx

from finwin.extractors import HTMLExtractor, PDFExtractor
from finwin.providers.base import (
    BaseProvider,
    ProviderResult,
    ProviderType,
    register_provider,
)

logger = logging.getLogger(__name__)


@register_provider("web")
class WebFetcherProvider(BaseProvider):
    """
    Fetches and extracts text from arbitrary URLs.
    
    Supports HTML pages and PDF documents.
    """
    
    name = "web"
    provider_type = ProviderType.WEB
    supports_symbol = False
    supports_query = False
    supports_batch = True  # Can fetch multiple URLs
    
    def __init__(
        self,
        timeout: int = 25,
        user_agent: str = (
            "Mozilla/5.0 (X11; Linux x86_64) "
            "Finwin/2.0"
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
    
    async def fetch_url(self, url: str) -> Dict[str, Any]:
        """
        Fetch a single URL and extract text.
        
        Args:
            url: URL to fetch
            
        Returns:
            Dict with url, status, content_type, extracted_text, error
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
            
            return {
                "url": url,
                "resolved_url": str(r.url) if str(r.url) != url else None,
                "status": status,
                "content_type": ct,
                "extracted_text": extracted_text,
                "error": error,
            }
            
        except Exception as e:
            logger.warning(f"Failed to fetch {url}: {e}")
            return {
                "url": url,
                "resolved_url": None,
                "status": -1,
                "content_type": "",
                "extracted_text": None,
                "error": str(e),
            }
    
    async def gather(
        self,
        symbol: Optional[str] = None,
        query: Optional[str] = None,
        **kwargs: Any,
    ) -> ProviderResult:
        """
        Fetch URLs and extract text.
        
        Args:
            symbol: Not used
            query: Not used
            **kwargs: Must include 'urls' list
            
        Returns:
            ProviderResult with fetch results
        """
        urls: List[str] = kwargs.get("urls", [])
        
        if not urls:
            return ProviderResult(
                provider_name=self.name,
                provider_type=self.provider_type,
                success=True,
                data={"fetches": [], "count": 0},
                raw_texts=[],
            )
        
        fetches: List[Dict[str, Any]] = []
        raw_texts: List[str] = []
        
        for url in urls:
            result = await self.fetch_url(url)
            fetches.append(result)
            
            if result.get("extracted_text"):
                raw_texts.append(
                    f"URL: {url}\n\n{result['extracted_text']}"
                )
        
        return ProviderResult(
            provider_name=self.name,
            provider_type=self.provider_type,
            success=True,
            data={
                "fetches": fetches,
                "count": len(fetches),
            },
            raw_texts=raw_texts,
            metadata={
                "urls_requested": len(urls),
                "urls_successful": sum(
                    1 for f in fetches if f.get("status", -1) == 200
                ),
            },
        )
    
    def get_tool_description(self) -> str:
        """Get description for LLM tool use."""
        return (
            "Fetch and extract text content from web URLs. "
            "Supports HTML pages and PDF documents. "
            "Provide a list of URLs to fetch."
        )
    
    def get_tool_parameters(self) -> Dict[str, Any]:
        """Get parameter schema for LLM tool use."""
        return {
            "type": "object",
            "properties": {
                "urls": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of URLs to fetch and extract text from",
                }
            },
            "required": ["urls"],
        }
