"""Google News RSS source for finwin."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

import httpx
import feedparser
from bs4 import BeautifulSoup

from finwin.models.context import NewsArticle, SourceResult
from finwin.sources.base import BaseSource, register_source

logger = logging.getLogger(__name__)


@register_source("google_news")
class GoogleNewsSource(BaseSource):
    """
    Fetches news from Google News RSS feed.
    
    Handles the Google News URL redirect resolution via batchexecute API.
    """
    
    name = "google_news"
    
    def __init__(
        self,
        max_items: int = 10,
        country: str = "IN",
        language: str = "en",
        timeout: int = 25,
        fetch_articles: bool = True,
    ):
        self.max_items = max_items
        self.country = country
        self.language = language
        self.timeout = timeout
        self.fetch_articles = fetch_articles
        self._client: Optional[httpx.AsyncClient] = None
    
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
    
    def _build_rss_url(self, query: str) -> str:
        """Build Google News RSS URL."""
        q = quote_plus(query)
        return (
            f"https://news.google.com/rss/search?q={q}"
            f"&hl={self.language}-{self.country}"
            f"&gl={self.country}"
            f"&ceid={self.country}:{self.language}"
        )
    
    async def _resolve_google_news_url(self, url: str) -> str:
        """
        Resolve Google News redirect URL to actual article URL.
        
        Uses Google's batchexecute API to get the real URL.
        """
        if "news.google.com/rss/articles/" not in url:
            return url
        
        client = await self._get_client()
        
        try:
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/132.0.0.0 Safari/537.36"
                ),
            }
            
            # Step 1: Fetch the Google News article page
            r = await client.get(url, headers=headers)
            if r.status_code != 200:
                logger.warning(f"Failed to fetch Google News page: {r.status_code}")
                return url
            
            # Step 2: Parse and extract data-p attribute
            soup = BeautifulSoup(r.text, "html.parser")
            cwiz = soup.find("c-wiz", attrs={"data-p": True})
            if not cwiz:
                logger.warning("Could not find c-wiz[data-p] element")
                return url
            
            data_p = cwiz.get("data-p")
            if not data_p:
                logger.warning("data-p attribute is empty")
                return url
            
            # Step 3: Parse the data-p JSON
            try:
                json_str = data_p.replace('%.@.', '["garturlreq",')
                obj = json.loads(json_str)
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse data-p JSON: {e}")
                return url
            
            # Step 4: Build the payload for batchexecute API
            req_data = obj[:-6] + obj[-2:]
            
            payload = {
                'f.req': json.dumps([
                    [["Fbv4je", json.dumps(req_data), "null", "generic"]]
                ])
            }
            
            post_headers = {
                "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
                "User-Agent": headers["User-Agent"],
            }
            
            # Step 5: Call the batchexecute API
            post_r = await client.post(
                "https://news.google.com/_/DotsSplashUi/data/batchexecute",
                data=payload,
                headers=post_headers,
            )
            
            if post_r.status_code != 200:
                logger.warning(f"batchexecute API returned {post_r.status_code}")
                return url
            
            # Step 6: Parse the response
            response_text = post_r.text
            if response_text.startswith(")]}'"):
                response_text = response_text[4:].strip()
            
            try:
                response_json = json.loads(response_text)
                array_string = response_json[0][2]
                inner_array = json.loads(array_string)
                article_url = inner_array[1]
                
                if article_url and article_url.startswith("http"):
                    logger.info(f"Resolved Google News URL: {article_url}")
                    return article_url
            except (json.JSONDecodeError, IndexError, KeyError, TypeError) as e:
                logger.warning(f"Failed to parse batchexecute response: {e}")
                return url
                
        except Exception as e:
            logger.warning(f"Failed to resolve Google News URL: {e}")
        
        return url
    
    async def gather(
        self,
        symbol: Optional[str] = None,
        query: Optional[str] = None,
        **kwargs: Any,
    ) -> SourceResult:
        """
        Gather news from Google News RSS.
        
        Args:
            symbol: Stock symbol (optional, used as fallback query)
            query: Search query
            **kwargs: Additional arguments (max_items override)
            
        Returns:
            SourceResult with news articles
        """
        search_query = query or symbol
        if not search_query:
            return SourceResult(
                name=self.name,
                success=False,
                error="No query provided",
            )
        
        max_items = kwargs.get("max_items", self.max_items)
        
        try:
            rss_url = self._build_rss_url(search_query)
            feed = feedparser.parse(rss_url)
            
            articles: List[NewsArticle] = []
            raw_texts: List[str] = []
            
            for entry in feed.entries[:max_items]:
                link = getattr(entry, "link", "")
                
                # Resolve Google News URL if needed
                resolved_link = await self._resolve_google_news_url(link)
                
                article = NewsArticle(
                    title=getattr(entry, "title", ""),
                    link=link,
                    resolved_link=resolved_link if resolved_link != link else None,
                    published=getattr(entry, "published", None),
                    source=(
                        getattr(entry, "source", {}).get("title")
                        if hasattr(entry, "source") else None
                    ),
                )
                articles.append(article)
            
            return SourceResult(
                name=self.name,
                success=True,
                data={
                    "articles": [a.model_dump() for a in articles],
                    "query": search_query,
                    "count": len(articles),
                },
                raw_texts=raw_texts,
            )
            
        except Exception as e:
            logger.exception(f"Failed to gather news: {e}")
            return SourceResult(
                name=self.name,
                success=False,
                error=str(e),
            )
