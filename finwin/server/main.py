"""FastAPI server for finwin context API."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from finwin.collector import ContextCollector
from finwin.models.context import StockContext
from finwin.models.macro import (
    MacroTimeSeries,
    MacroDataPoint,
    CountryInfo,
    MacroIndicatorInfo,
    GlobalGDPSummary,
    MacroDashboardData,
)
from finwin.config.settings import get_settings
from finwin.providers.financials.yfinance import YFinanceProvider
from finwin.providers.news.google import GoogleNewsProvider
from finwin.providers.web.fetcher import WebFetcherProvider
from finwin.providers.macro.worldbank import WorldBankProvider

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


# =============================================================================
# Macro Dashboard Endpoints
# =============================================================================

# Global provider instance (reused across requests)
_worldbank_provider: Optional[WorldBankProvider] = None


def get_worldbank_provider() -> WorldBankProvider:
    """Get or create World Bank provider instance."""
    global _worldbank_provider
    if _worldbank_provider is None:
        _worldbank_provider = WorldBankProvider()
    return _worldbank_provider


@app.get("/api/macro/indicators", response_model=List[MacroIndicatorInfo])
async def get_macro_indicators() -> List[MacroIndicatorInfo]:
    """Get list of available macroeconomic indicators."""
    provider = get_worldbank_provider()
    return await provider.get_indicators()


@app.get("/api/macro/countries", response_model=List[CountryInfo])
async def get_macro_countries() -> List[CountryInfo]:
    """Get list of available countries."""
    provider = get_worldbank_provider()
    return await provider.get_countries()


@app.get("/api/macro/gdp/{country}", response_model=MacroTimeSeries)
async def get_country_gdp(
    country: str,
    start_year: Optional[int] = Query(None, description="Start year"),
    end_year: Optional[int] = Query(None, description="End year"),
) -> MacroTimeSeries:
    """Get GDP time series for a specific country."""
    provider = get_worldbank_provider()
    try:
        return await provider.get_indicator(
            indicator="gdp",
            country=country,
            start_year=start_year,
            end_year=end_year,
        )
    except Exception as e:
        logger.exception(f"Error fetching GDP for {country}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/macro/indicator/{indicator}/{country}", response_model=MacroTimeSeries)
async def get_indicator_data(
    indicator: str,
    country: str,
    start_year: Optional[int] = Query(None, description="Start year"),
    end_year: Optional[int] = Query(None, description="End year"),
) -> MacroTimeSeries:
    """Get time series for any indicator and country."""
    provider = get_worldbank_provider()
    try:
        return await provider.get_indicator(
            indicator=indicator,
            country=country,
            start_year=start_year,
            end_year=end_year,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Error fetching {indicator} for {country}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/macro/dashboard", response_model=MacroDashboardData)
async def get_macro_dashboard(
    start_year: Optional[int] = Query(None, description="Start year (default: 20 years ago)"),
    end_year: Optional[int] = Query(None, description="End year (default: current year)"),
    top_n: int = Query(20, description="Number of top countries to include", ge=5, le=200),
) -> MacroDashboardData:
    """
    Get aggregated macro dashboard data.
    
    Returns:
    - World GDP total and history
    - Top N economies by GDP
    - Regional breakdown
    - All country GDP data for charts
    """
    provider = get_worldbank_provider()
    
    try:
        # Get default year range
        current_year = datetime.now().year
        start = start_year or (current_year - 20)
        end = end_year or current_year
        
        # Get all GDP data
        gdp_by_country = await provider.get_gdp_all_countries(
            start_year=start,
            end_year=end,
        )
        
        logger.info(f"GDP data loaded for {len(gdp_by_country)} entities")
        
        # Get world GDP
        world_gdp = await provider.get_indicator(
            indicator="gdp",
            country="WLD",
            start_year=start,
            end_year=end,
        )
        
        # Get countries for metadata
        countries = await provider.get_countries()
        
        # Create lookups by both code and name
        country_by_code = {c.code: c for c in countries}
        country_by_name = {c.name: c for c in countries}
        
        logger.info(f"Countries metadata loaded: {len(countries)} countries")
        
        # Calculate world GDP summary
        latest_world = world_gdp.get_latest()
        world_history = world_gdp.data
        
        # Calculate growth rate
        world_growth = None
        if latest_world:
            world_growth = world_gdp.get_growth_rate(latest_world.year)
        
        # Find top countries by latest GDP
        # Match by code first, then by name if not found
        country_latest_gdp = []
        for code, ts in gdp_by_country.items():
            latest = ts.get_latest()
            if latest and latest.value:
                # Try to find country metadata
                info = country_by_code.get(code)
                if not info:
                    # Try matching by name (GDP data has country_name)
                    info = country_by_name.get(ts.country_name)
                
                if info:
                    growth = ts.get_growth_rate(latest.year)
                    country_latest_gdp.append(CountryInfo(
                        code=code,
                        name=info.name,
                        region=info.region,
                        income_level=info.income_level,
                        capital=info.capital,
                        latest_gdp=latest.value,
                        latest_gdp_year=latest.year,
                        gdp_growth=growth,
                    ))
                elif ts.country_name and len(code) <= 3:
                    # Include country even without full metadata
                    # (filter out obvious aggregates which have short codes like ZH)
                    growth = ts.get_growth_rate(latest.year)
                    country_latest_gdp.append(CountryInfo(
                        code=code,
                        name=ts.country_name,
                        region="",
                        income_level="",
                        capital="",
                        latest_gdp=latest.value,
                        latest_gdp_year=latest.year,
                        gdp_growth=growth,
                    ))
        
        logger.info(f"Countries with GDP data: {len(country_latest_gdp)}")
        
        # Sort by GDP and take top N
        top_countries = sorted(
            country_latest_gdp,
            key=lambda x: x.latest_gdp or 0,
            reverse=True,
        )[:top_n]
        
        # Calculate regional totals
        region_totals: Dict[str, float] = {}
        for c in country_latest_gdp:
            if c.region and c.latest_gdp:
                region_totals[c.region] = region_totals.get(c.region, 0) + c.latest_gdp
        
        # Build response
        summary = GlobalGDPSummary(
            world_gdp_total=latest_world.value if latest_world else None,
            world_gdp_year=latest_world.year if latest_world else None,
            world_gdp_growth=world_growth,
            world_gdp_history=world_history,
            top_countries=top_countries,
            region_totals=region_totals,
            data_source="World Bank",
            last_updated=datetime.utcnow().isoformat(),
            countries_count=len(country_latest_gdp),
        )
        
        # Only include top countries' GDP data to reduce payload
        filtered_gdp = {
            code: gdp_by_country[code]
            for code in [c.code for c in top_countries]
            if code in gdp_by_country
        }
        
        return MacroDashboardData(
            gdp_summary=summary,
            countries=top_countries,
            gdp_by_country=filtered_gdp,
        )
        
    except Exception as e:
        logger.exception("Error building macro dashboard")
        raise HTTPException(status_code=500, detail=str(e))


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    global _worldbank_provider
    if _worldbank_provider:
        await _worldbank_provider.close()


if __name__ == "__main__":
    main()
