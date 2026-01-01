"""
finwin - Financial Context Collector

A library for gathering structured context (news, financials, web content)
about stocks and companies.
"""

from finwin.collector import ContextCollector
from finwin.models.context import StockContext, NewsArticle, Financials, FetchResult
from finwin.models.config import CollectorConfig

__version__ = "0.1.0"
__all__ = [
    "ContextCollector",
    "StockContext",
    "NewsArticle", 
    "Financials",
    "FetchResult",
    "CollectorConfig",
]
