"""FastAPI server for finwin context API."""

from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from finwin.collector import ContextCollector
from finwin.models.context import StockContext
from finwin.config.settings import get_settings
from finwin.providers.financials.yfinance import YFinanceProvider
from finwin.providers.news.google import GoogleNewsProvider
from finwin.providers.web.fetcher import WebFetcherProvider

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()

app = FastAPI(
    title="Finwin Context API",
    description="API for gathering financial context about stocks/companies",
    version="2.0.0",
)

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.server.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ContextRequest(BaseModel):
    """Request body for context gathering."""
    
    symbol: Optional[str] = None
    query: Optional[str] = None
    extra_urls: Optional[List[str]] = None
    news_count: int = 10


class HealthResponse(BaseModel):
    """Health check response."""
    
    status: str = "healthy"
    version: str = "1.0.0"


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse()


@app.get("/api/context", response_model=StockContext)
async def get_context(
    symbol: Optional[str] = Query(None, description="Stock symbol (e.g., TCS.NS, AAPL)"),
    query: Optional[str] = Query(None, description="Search query (e.g., company name)"),
    news_count: int = Query(10, description="Number of news articles to fetch", ge=1, le=50),
) -> StockContext:
    """
    Gather financial context for a stock/company.
    
    Returns news articles, financial data, and aggregated text
    suitable for LLM consumption.
    """
    if not symbol and not query:
        raise HTTPException(
            status_code=400,
            detail="At least one of 'symbol' or 'query' must be provided",
        )
    
    try:
        # Create collector with providers
        async with ContextCollector(
            sources=[
                GoogleNewsProvider(max_items=news_count),
                YFinanceProvider(),
                WebFetcherProvider(),
            ]
        ) as collector:
            context = await collector.gather(
                symbol=symbol,
                query=query,
            )
            return context
    except Exception as e:
        logger.exception("Error gathering context")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/context", response_model=StockContext)
async def post_context(request: ContextRequest) -> StockContext:
    """
    Gather financial context for a stock/company (POST version).
    
    Allows specifying extra URLs to fetch.
    """
    if not request.symbol and not request.query:
        raise HTTPException(
            status_code=400,
            detail="At least one of 'symbol' or 'query' must be provided",
        )
    
    try:
        async with ContextCollector(
            sources=[
                GoogleNewsProvider(max_items=request.news_count),
                YFinanceProvider(),
                WebFetcherProvider(),
            ]
        ) as collector:
            context = await collector.gather(
                symbol=request.symbol,
                query=request.query,
                extra_urls=request.extra_urls,
            )
            return context
    except Exception as e:
        logger.exception("Error gathering context")
        raise HTTPException(status_code=500, detail=str(e))


def main() -> None:
    """Run the server with uvicorn."""
    import uvicorn
    uvicorn.run(
        app,
        host=settings.server.host,
        port=settings.server.port,
        reload=settings.server.reload,
    )


if __name__ == "__main__":
    main()
