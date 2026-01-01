"""Macro dashboard API routes."""

from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from finwin.models.macro import (
    MacroTimeSeries,
    CountryInfo,
    MacroIndicatorInfo,
    MacroDashboardData,
)
from finwin.providers.macro.worldbank import WorldBankProvider
from finwin.services.macro_dashboard import build_macro_dashboard

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/macro", tags=["macro"])

# Global provider instance (reused across requests)
_worldbank_provider: Optional[WorldBankProvider] = None


def get_worldbank_provider() -> WorldBankProvider:
    """Get or create World Bank provider instance."""
    global _worldbank_provider
    if _worldbank_provider is None:
        _worldbank_provider = WorldBankProvider()
    return _worldbank_provider


@router.get("/indicators", response_model=List[MacroIndicatorInfo])
async def get_macro_indicators() -> List[MacroIndicatorInfo]:
    """Get list of available macroeconomic indicators."""
    provider = get_worldbank_provider()
    return await provider.get_indicators()


@router.get("/countries", response_model=List[CountryInfo])
async def get_macro_countries() -> List[CountryInfo]:
    """Get list of available countries."""
    provider = get_worldbank_provider()
    return await provider.get_countries()


@router.get("/gdp/{country}", response_model=MacroTimeSeries)
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


@router.get("/indicator/{indicator}/{country}", response_model=MacroTimeSeries)
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


@router.get("/dashboard", response_model=MacroDashboardData)
async def get_macro_dashboard(
    start_year: Optional[int] = Query(
        None, description="Start year (default: 20 years ago)"
    ),
    end_year: Optional[int] = Query(
        None, description="End year (default: current year)"
    ),
    top_n: int = Query(
        20, description="Number of top countries to include", ge=5, le=500
    ),
) -> MacroDashboardData:
    """
    Get aggregated macro dashboard data.
    
    Returns world GDP total/history, top N economies, and regional breakdown.
    """
    provider = get_worldbank_provider()
    try:
        return await build_macro_dashboard(
            provider=provider,
            start_year=start_year,
            end_year=end_year,
            top_n=top_n,
        )
    except Exception as e:
        logger.exception("Error building macro dashboard")
        raise HTTPException(status_code=500, detail=str(e))


async def shutdown() -> None:
    """Cleanup provider on shutdown."""
    global _worldbank_provider
    if _worldbank_provider:
        await _worldbank_provider.close()
