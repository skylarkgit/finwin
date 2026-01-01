# finwin

A Python library for gathering structured financial context (news, financials, web content) about stocks and companies.

## Features

- **Async-first**: Built with `httpx` and `asyncio` for fast, concurrent data fetching
- **Pluggable sources**: Easy to add new data sources (news, financials, social media, etc.)
- **Structured output**: Pydantic models for type safety and easy JSON serialization
- **Caching**: Built-in TTL-based caching to avoid repeated API calls
- **CLI included**: Command-line interface for quick data gathering

## Installation

```bash
# Using pip
pip install -e .

# Or with conda
conda env create -f environment.yml
conda activate finwin
pip install -e .
```

## Quick Start

### As a Library

```python
import asyncio
from finwin import ContextCollector, StockContext
from finwin.sources import GoogleNewsSource, YFinanceSource
from finwin.cache import InMemoryCache

async def main():
    collector = ContextCollector(
        sources=[
            GoogleNewsSource(max_items=10, country="IN"),
            YFinanceSource(),
        ],
        cache=InMemoryCache(default_ttl=300),
    )
    
    async with collector:
        context: StockContext = await collector.gather(
            symbol="TCS.NS",
            query="TCS",
        )
    
    # Access structured data
    print(context.financials.market_cap)
    print(context.news[0].title)
    
    # Serialize to JSON
    print(context.model_dump_json(indent=2))

asyncio.run(main())
```

### CLI Usage

```bash
# Basic usage
finwin --symbol TCS.NS --name "TCS"

# With options
finwin --symbol AAPL --news-items 5 --pretty

# Fetch additional URLs
finwin --symbol RELIANCE.NS --urls https://example.com/report.pdf

# Output to file
finwin --symbol TCS.NS --output context.json --pretty
```

## Architecture

```
finwin/
├── __init__.py           # Public API
├── collector.py          # Main orchestrator
├── models/
│   ├── context.py        # StockContext, NewsArticle, Financials
│   └── config.py         # CollectorConfig
├── sources/
│   ├── base.py           # BaseSource ABC + registry
│   ├── news/google.py    # Google News RSS
│   ├── financials/yfinance.py  # Yahoo Finance
│   └── web/fetcher.py    # Generic URL fetcher
├── extractors/
│   ├── html.py           # HTML text extraction
│   └── pdf.py            # PDF text extraction
├── cache/
│   ├── base.py           # BaseCache ABC
│   └── memory.py         # In-memory TTL cache
└── cli.py                # Command-line interface
```

## Adding Custom Sources

```python
from finwin.sources import BaseSource, register_source
from finwin.models.context import SourceResult

@register_source("reddit")
class RedditSource(BaseSource):
    name = "reddit"
    
    async def gather(self, symbol=None, query=None, **kwargs) -> SourceResult:
        # Your implementation here
        posts = await self._fetch_posts(query)
        return SourceResult(
            name=self.name,
            success=True,
            data={"posts": posts},
            raw_texts=[p.text for p in posts],
        )
```

## Data Models

### StockContext

The main output object containing:

- `meta`: Metadata (label, symbol, query, timestamp)
- `financials`: Structured financial data (market cap, P/E, etc.)
- `news`: List of `NewsArticle` objects
- `fetches`: List of `FetchResult` from URL fetching
- `source_results`: Raw results from each source
- `all_texts`: Aggregated text from all sources (for LLM consumption)

### NewsArticle

```python
class NewsArticle:
    title: str
    link: str
    resolved_link: Optional[str]  # Actual URL after resolving redirects
    published: Optional[str]
    source: Optional[str]
    extracted_text: Optional[str]
```

### Financials

```python
class Financials:
    symbol: str
    short_name: Optional[str]
    long_name: Optional[str]
    sector: Optional[str]
    industry: Optional[str]
    market_cap: Optional[float]
    current_price: Optional[float]
    trailing_pe: Optional[float]
    # ... and more
```

## License

MIT
