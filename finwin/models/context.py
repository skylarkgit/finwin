"""Core data models for finwin context."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class NewsArticle(BaseModel):
    """A news article with metadata and optional extracted text."""
    
    title: str
    link: str
    resolved_link: Optional[str] = None
    published: Optional[str] = None
    source: Optional[str] = None
    extracted_text: Optional[str] = None


class FetchResult(BaseModel):
    """Result of fetching a URL."""
    
    url: str
    resolved_url: Optional[str] = None
    status: int
    content_type: str = ""
    extracted_text: Optional[str] = None
    error: Optional[str] = None


class Financials(BaseModel):
    """Financial data from various sources."""
    
    symbol: str
    ok: bool = False
    error: Optional[str] = None
    
    # Basic info
    short_name: Optional[str] = None
    long_name: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    website: Optional[str] = None
    
    # Market data
    market_cap: Optional[float] = None
    currency: Optional[str] = None
    exchange: Optional[str] = None
    quote_type: Optional[str] = None
    
    # Valuation
    trailing_pe: Optional[float] = None
    forward_pe: Optional[float] = None
    price_to_book: Optional[float] = None
    
    # Price
    current_price: Optional[float] = None
    previous_close: Optional[float] = None
    fifty_two_week_high: Optional[float] = None
    fifty_two_week_low: Optional[float] = None
    
    # Other
    beta: Optional[float] = None
    dividend_yield: Optional[float] = None
    
    # Raw data from source (for flexibility)
    raw_financials: Optional[Dict[str, Any]] = None
    raw_quarterly_financials: Optional[Dict[str, Any]] = None
    raw_balance_sheet: Optional[Dict[str, Any]] = None
    raw_cashflow: Optional[Dict[str, Any]] = None


class SourceResult(BaseModel):
    """Result from a single data source."""
    
    name: str
    success: bool = True
    error: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)
    raw_texts: List[str] = Field(default_factory=list)


class Meta(BaseModel):
    """Metadata about the context collection."""
    
    label: str
    symbol: Optional[str] = None
    query: Optional[str] = None
    generated_at_utc: datetime = Field(default_factory=lambda: datetime.utcnow())


class StockContext(BaseModel):
    """
    Complete context for a stock/company.
    
    This is the main output of the ContextCollector.
    """
    
    meta: Meta
    financials: Optional[Financials] = None
    news: List[NewsArticle] = Field(default_factory=list)
    fetches: List[FetchResult] = Field(default_factory=list)
    source_results: List[SourceResult] = Field(default_factory=list)
    
    # Aggregated raw text from all sources (for LLM consumption)
    all_texts: List[str] = Field(default_factory=list)
    
    def add_source_result(self, result: SourceResult) -> None:
        """Add a source result and aggregate its texts."""
        self.source_results.append(result)
        self.all_texts.extend(result.raw_texts)
