"""Macro dashboard business logic."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Dict, Optional

from finwin.models.macro import (
    MacroTimeSeries,
    CountryInfo,
    GlobalGDPSummary,
    MacroDashboardData,
)
from finwin.providers.macro.worldbank import WorldBankProvider

logger = logging.getLogger(__name__)


async def build_macro_dashboard(
    provider: WorldBankProvider,
    start_year: Optional[int] = None,
    end_year: Optional[int] = None,
    top_n: int = 20,
) -> MacroDashboardData:
    """
    Build aggregated macro dashboard data.
    
    Args:
        provider: World Bank provider instance
        start_year: Start year for data range
        end_year: End year for data range
        top_n: Number of top countries to include
        
    Returns:
        MacroDashboardData with summary, countries, and GDP data
    """
    current_year = datetime.now().year
    start = start_year or (current_year - 20)
    end = end_year or current_year
    
    # Fetch all data concurrently
    gdp_by_country = await provider.get_gdp_all_countries(start_year=start, end_year=end)
    world_gdp = await provider.get_indicator(indicator="gdp", country="WLD", start_year=start, end_year=end)
    countries = await provider.get_countries()
    
    logger.info(f"GDP data loaded for {len(gdp_by_country)} entities")
    logger.info(f"Countries metadata loaded: {len(countries)} countries")
    
    # Build lookup tables
    country_by_code = {c.code: c for c in countries}
    country_by_name = {c.name: c for c in countries}
    
    # Calculate world GDP summary
    latest_world = world_gdp.get_latest()
    world_growth = world_gdp.get_growth_rate(latest_world.year) if latest_world else None
    
    # Build country GDP list with metadata
    country_latest_gdp = _build_country_gdp_list(
        gdp_by_country, country_by_code, country_by_name
    )
    
    logger.info(f"Countries with GDP data: {len(country_latest_gdp)}")
    
    # Sort and select top N
    top_countries = sorted(
        country_latest_gdp, key=lambda x: x.latest_gdp or 0, reverse=True
    )[:top_n]
    
    # Calculate regional totals
    region_totals = _calculate_region_totals(country_latest_gdp)
    
    # Build summary
    summary = GlobalGDPSummary(
        world_gdp_total=latest_world.value if latest_world else None,
        world_gdp_year=latest_world.year if latest_world else None,
        world_gdp_growth=world_growth,
        world_gdp_history=world_gdp.data,
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


def _build_country_gdp_list(
    gdp_by_country: Dict[str, MacroTimeSeries],
    country_by_code: Dict[str, CountryInfo],
    country_by_name: Dict[str, CountryInfo],
) -> list[CountryInfo]:
    """Build list of countries with their latest GDP data."""
    result = []
    
    for code, ts in gdp_by_country.items():
        latest = ts.get_latest()
        if not latest or not latest.value:
            continue
            
        # Try to find country metadata by code first, then by name
        info = country_by_code.get(code) or country_by_name.get(ts.country_name)
        growth = ts.get_growth_rate(latest.year)
        
        if info:
            result.append(CountryInfo(
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
            # (filter out aggregates which have short codes like ZH)
            result.append(CountryInfo(
                code=code,
                name=ts.country_name,
                region="",
                income_level="",
                capital="",
                latest_gdp=latest.value,
                latest_gdp_year=latest.year,
                gdp_growth=growth,
            ))
    
    return result


def _calculate_region_totals(countries: list[CountryInfo]) -> Dict[str, float]:
    """Calculate total GDP by region."""
    totals: Dict[str, float] = {}
    for c in countries:
        if c.region and c.latest_gdp:
            totals[c.region] = totals.get(c.region, 0) + c.latest_gdp
    return totals
