"""
finwin - Financial Context Platform

A comprehensive library for:
- Gathering structured context (news, financials, web content) about stocks
- Orchestrating AI agents with LLM-powered workflows
- Executing actions based on financial data analysis

Architecture:
- providers/: Data providers (news, financials, web scraping, APIs)
- extractors/: Text extraction from various formats
- llm/: LLM abstraction layer (multi-provider support)
- agents/: AI agents that use providers and LLMs
- actions/: Side effects agents can trigger
- config/: Centralized configuration management
- cache/: Caching implementations
- server/: FastAPI server
"""

__version__ = "2.0.0"

# Core collector (legacy API, still works)
from finwin.collector import ContextCollector

# Models
from finwin.models.context import (
    StockContext,
    NewsArticle,
    Financials,
    FetchResult,
)
from finwin.models.config import CollectorConfig

# Configuration
from finwin.config.settings import Settings, get_settings

# Providers (new architecture)
from finwin.providers.base import (
    BaseProvider,
    ProviderRegistry,
    ProviderResult,
    ProviderType,
    register_provider,
)
from finwin.providers.news.google import GoogleNewsProvider
from finwin.providers.financials.yfinance import YFinanceProvider
from finwin.providers.web.fetcher import WebFetcherProvider

# LLM (lazy imports to avoid optional dependency issues)
# Use: from finwin.llm import BaseLLM, create_llm

# Agents (lazy imports)
# Use: from finwin.agents import BaseAgent

# Actions (lazy imports)
# Use: from finwin.actions import BaseAction

__all__ = [
    # Version
    "__version__",
    # Collector
    "ContextCollector",
    # Models
    "StockContext",
    "NewsArticle",
    "Financials",
    "FetchResult",
    "CollectorConfig",
    # Config
    "Settings",
    "get_settings",
    # Providers
    "BaseProvider",
    "ProviderRegistry",
    "ProviderResult",
    "ProviderType",
    "register_provider",
    "GoogleNewsProvider",
    "YFinanceProvider",
    "WebFetcherProvider",
]
