#!/usr/bin/env python3
"""
Basic usage example for finwin library.

This demonstrates how to use finwin as a library (not CLI).
"""

import asyncio
import json

from finwin import ContextCollector, StockContext
from finwin.sources import GoogleNewsSource, YFinanceSource, WebFetcher
from finwin.cache import InMemoryCache


async def main():
    """Gather context for a stock."""
    
    # Create sources
    news_source = GoogleNewsSource(
        max_items=5,
        country="IN",
        language="en",
    )
    
    financials_source = YFinanceSource()
    
    web_source = WebFetcher()
    
    # Create collector with caching
    cache = InMemoryCache(default_ttl=300)  # 5 minute cache
    
    async with ContextCollector(
        sources=[news_source, financials_source, web_source],
        cache=cache,
    ) as collector:
        
        # Gather context
        context: StockContext = await collector.gather(
            symbol="TCS.NS",
            query="TCS Tata Consultancy",
            extra_urls=[
                "https://www.tcs.com/who-we-are/newsroom",
            ],
        )
    
    # Access structured data
    print(f"Company: {context.meta.label}")
    print(f"Symbol: {context.meta.symbol}")
    print(f"Generated at: {context.meta.generated_at_utc}")
    print()
    
    if context.financials:
        print("=== Financials ===")
        print(f"Name: {context.financials.long_name}")
        print(f"Sector: {context.financials.sector}")
        print(f"Market Cap: {context.financials.market_cap}")
        print(f"Current Price: {context.financials.current_price}")
        print(f"P/E Ratio: {context.financials.trailing_pe}")
        print()
    
    print(f"=== News ({len(context.news)} articles) ===")
    for article in context.news[:3]:
        print(f"- {article.title}")
        if article.resolved_link:
            print(f"  URL: {article.resolved_link}")
        print()
    
    print(f"=== Fetched URLs ({len(context.fetches)}) ===")
    for fetch in context.fetches:
        status = "✓" if fetch.status == 200 else "✗"
        print(f"{status} {fetch.url[:60]}...")
        if fetch.error:
            print(f"  Error: {fetch.error}")
    print()
    
    print(f"=== Source Results ===")
    for result in context.source_results:
        status = "✓" if result.success else "✗"
        print(f"{status} {result.name}: {len(result.raw_texts)} texts")
    print()
    
    # Serialize to JSON (for API response or storage)
    print("=== JSON Output (truncated) ===")
    json_str = context.model_dump_json(indent=2)
    print(json_str[:500] + "...")


if __name__ == "__main__":
    asyncio.run(main())
