"""Data providers for finwin - APIs, scrapers, and data sources."""

from finwin.providers.base import (
    BaseProvider,
    ProviderRegistry,
    ProviderResult,
    register_provider,
)

__all__ = [
    "BaseProvider",
    "ProviderRegistry",
    "ProviderResult",
    "register_provider",
]

# Import providers to register them
from finwin.providers.news import google  # noqa: F401
from finwin.providers.financials import yfinance  # noqa: F401
from finwin.providers.web import fetcher  # noqa: F401
