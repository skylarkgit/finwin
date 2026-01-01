"""Main context collector for finwin."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, List, Optional, Union

from finwin.cache.base import BaseCache
from finwin.models.config import CollectorConfig
from finwin.models.context import (
    Financials,
    Meta,
    NewsArticle,
    SourceResult,
    StockContext,
)

# Import both for backwards compatibility
from finwin.sources.base import BaseSource
from finwin.providers.base import BaseProvider, ProviderResult

logger = logging.getLogger(__name__)

# Type alias for sources (supports both old and new)
DataSource = Union[BaseSource, BaseProvider]


class ContextCollector:
    """
    Main orchestrator for gathering stock context.
    
    Coordinates multiple data sources/providers and aggregates results
    into a unified StockContext object.
    
    Supports both legacy sources and new providers.
    
    Example:
        ```python
        from finwin import ContextCollector
        from finwin.providers import GoogleNewsProvider, YFinanceProvider
        
        collector = ContextCollector(
            sources=[
                GoogleNewsProvider(max_items=10),
                YFinanceProvider(),
            ]
        )
        
        context = await collector.gather(
            symbol="TCS.NS",
            query="TCS",
        )
        ```
    """
    
    def __init__(
        self,
        sources: Optional[List[DataSource]] = None,
        config: Optional[CollectorConfig] = None,
        cache: Optional[BaseCache] = None,
    ):
        """
        Initialize collector.
        
        Args:
            sources: List of data sources/providers to use
            config: Configuration settings
            cache: Optional cache implementation
        """
        self.sources = sources or []
        self.config = config or CollectorConfig()
        self.cache = cache
    
    def add_source(self, source: DataSource) -> "ContextCollector":
        """
        Add a data source/provider.
        
        Args:
            source: Source to add
            
        Returns:
            Self for chaining
        """
        self.sources.append(source)
        return self
    
    async def gather(
        self,
        symbol: Optional[str] = None,
        query: Optional[str] = None,
        extra_urls: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> StockContext:
        """
        Gather context from all configured sources.
        
        Args:
            symbol: Stock symbol (e.g., "TCS.NS", "AAPL")
            query: Search query (e.g., company name)
            extra_urls: Additional URLs to fetch
            **kwargs: Additional arguments passed to sources
            
        Returns:
            StockContext with aggregated data
        """
        label = query or symbol or "stock"
        
        # Check cache first
        if self.cache:
            cache_key = self.cache.make_key(
                "context", symbol or "", query or ""
            )
            cached = await self.cache.get(cache_key)
            if cached:
                logger.info(f"Cache hit for {cache_key}")
                return StockContext.model_validate(cached)
        
        # Create context object
        context = StockContext(
            meta=Meta(
                label=label,
                symbol=symbol,
                query=query,
                generated_at_utc=datetime.now(timezone.utc),
            )
        )
        
        # Gather from all sources concurrently
        if self.sources:
            tasks = [
                self._gather_from_source(
                    source, symbol, query, extra_urls, **kwargs
                )
                for source in self.sources
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(
                        f"Source {self.sources[i].name} failed: {result}"
                    )
                    context.add_source_result(SourceResult(
                        name=self.sources[i].name,
                        success=False,
                        error=str(result),
                    ))
                else:
                    # Convert ProviderResult to SourceResult if needed
                    source_result = self._to_source_result(result)
                    context.add_source_result(source_result)
                    
                    # Extract structured data
                    self._process_source_result(context, source_result)
        
        # Cache the result
        if self.cache:
            await self.cache.set(
                cache_key,
                context.model_dump(),
                ttl=self.config.cache_ttl,
            )
        
        return context
    
    def _to_source_result(
        self,
        result: Union[SourceResult, ProviderResult],
    ) -> SourceResult:
        """Convert ProviderResult to SourceResult for compatibility."""
        if isinstance(result, SourceResult):
            return result
        
        # Convert ProviderResult to SourceResult
        return SourceResult(
            name=result.provider_name,
            success=result.success,
            error=result.error,
            data=result.data,
            raw_texts=result.raw_texts,
        )
    
    async def _gather_from_source(
        self,
        source: DataSource,
        symbol: Optional[str],
        query: Optional[str],
        extra_urls: Optional[List[str]],
        **kwargs: Any,
    ) -> Union[SourceResult, ProviderResult]:
        """Gather data from a single source."""
        # Pass extra_urls to web fetcher
        if source.name == "web" and extra_urls:
            kwargs["urls"] = extra_urls
        
        return await source.gather(symbol=symbol, query=query, **kwargs)
    
    def _process_source_result(
        self,
        context: StockContext,
        result: SourceResult,
    ) -> None:
        """Extract structured data from source results."""
        if result.name == "yfinance" and result.success:
            # Extract financials
            fin_data = result.data.get("financials")
            if fin_data:
                context.financials = Financials.model_validate(fin_data)
        
        elif result.name == "google_news" and result.success:
            # Extract news articles
            articles_data = result.data.get("articles", [])
            for article_data in articles_data:
                context.news.append(
                    NewsArticle.model_validate(article_data)
                )
        
        elif result.name == "web" and result.success:
            # Extract fetch results
            from finwin.models.context import FetchResult
            fetches_data = result.data.get("fetches", [])
            for fetch_data in fetches_data:
                context.fetches.append(
                    FetchResult.model_validate(fetch_data)
                )
    
    async def close(self) -> None:
        """Close all sources and release resources."""
        for source in self.sources:
            try:
                await source.close()
            except Exception as e:
                logger.warning(f"Error closing source {source.name}: {e}")
    
    async def __aenter__(self) -> "ContextCollector":
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()
