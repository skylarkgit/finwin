"""Data sources for finwin."""

from finwin.sources.base import BaseSource, SourceRegistry, register_source
from finwin.sources.news.google import GoogleNewsSource
from finwin.sources.financials.yfinance import YFinanceSource
from finwin.sources.web.fetcher import WebFetcher

__all__ = [
    "BaseSource",
    "SourceRegistry",
    "register_source",
    "GoogleNewsSource",
    "YFinanceSource",
    "WebFetcher",
]
