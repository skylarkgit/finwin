"""Macro dashboard business logic."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Dict, List, Optional

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
    Build aggregated macro dashboard data with multiple indicators.
    
    Fetches indicators sequentially to avoid overwhelming the API.
    If extra indicators fail, continues with just GDP data.
    """
    current_year = datetime.now().year
    start = start_year or (current_year - 20)
    end = end_year or current_year
    
    # Fetch GDP first (required)
    logger.info("Fetching GDP data...")
    gdp_by_country = await provider.get_indicator_all_countries(
        "gdp", start, end
    )
    logger.info(f"GDP data loaded for {len(gdp_by_country)} entities")
    
    # Fetch world GDP for summary
    logger.info("Fetching World GDP...")
    world_gdp = await provider.get_indicator("gdp", "WLD", start, end)
    
    # Fetch countries metadata
    logger.info("Fetching countries metadata...")
    countries = await provider.get_countries()
    logger.info(f"Countries metadata: {len(countries)} countries")
    
    # Fetch optional indicators with fallback
    pop_by_country: Dict[str, MacroTimeSeries] = {}
    gdp_pc_by_country: Dict[str, MacroTimeSeries] = {}
    fdi_in_by_country: Dict[str, MacroTimeSeries] = {}
    fdi_out_by_country: Dict[str, MacroTimeSeries] = {}
    exports_by_country: Dict[str, MacroTimeSeries] = {}
    imports_by_country: Dict[str, MacroTimeSeries] = {}
    
    try:
        logger.info("Fetching population data...")
        pop_by_country = await provider.get_indicator_all_countries(
            "population", start, end
        )
        logger.info(f"Population data loaded for {len(pop_by_country)} entities")
    except Exception as e:
        logger.warning(f"Failed to fetch population data: {e}")
    
    try:
        logger.info("Fetching GDP per capita data...")
        gdp_pc_by_country = await provider.get_indicator_all_countries(
            "gdp_per_capita", start, end
        )
        logger.info(f"GDP/capita loaded for {len(gdp_pc_by_country)} entities")
    except Exception as e:
        logger.warning(f"Failed to fetch GDP per capita data: {e}")
    
    # FDI data (Foreign Direct Investment)
    try:
        logger.info("Fetching FDI inflows data...")
        fdi_in_by_country = await provider.get_indicator_all_countries(
            "fdi_inflows", start, end
        )
        logger.info(f"FDI inflows loaded for {len(fdi_in_by_country)} entities")
    except Exception as e:
        logger.warning(f"Failed to fetch FDI inflows: {e}")
    
    try:
        logger.info("Fetching FDI outflows data...")
        fdi_out_by_country = await provider.get_indicator_all_countries(
            "fdi_outflows", start, end
        )
        logger.info(f"FDI outflows loaded for {len(fdi_out_by_country)} entities")
    except Exception as e:
        logger.warning(f"Failed to fetch FDI outflows: {e}")
    
    # Trade data (exports/imports)
    try:
        logger.info("Fetching exports data...")
        exports_by_country = await provider.get_indicator_all_countries(
            "exports", start, end
        )
        logger.info(f"Exports loaded for {len(exports_by_country)} entities")
    except Exception as e:
        logger.warning(f"Failed to fetch exports: {e}")
    
    try:
        logger.info("Fetching imports data...")
        imports_by_country = await provider.get_indicator_all_countries(
            "imports", start, end
        )
        logger.info(f"Imports loaded for {len(imports_by_country)} entities")
    except Exception as e:
        logger.warning(f"Failed to fetch imports: {e}")
    
    # Build lookup tables
    country_by_code = {c.code: c for c in countries}
    country_by_name = {c.name: c for c in countries}
    
    # Calculate world GDP summary
    latest_world = world_gdp.get_latest()
    world_growth = None
    if latest_world:
        world_growth = world_gdp.get_growth_rate(latest_world.year)
    
    # Build country list with all available indicators
    country_list = _build_country_list(
        gdp_by_country,
        pop_by_country,
        gdp_pc_by_country,
        fdi_in_by_country,
        fdi_out_by_country,
        exports_by_country,
        imports_by_country,
        country_by_code,
        country_by_name,
    )
    
    logger.info(f"Countries with data: {len(country_list)}")
    
    # Sort by GDP and take top N
    top_countries = sorted(
        country_list, key=lambda x: x.latest_gdp or 0, reverse=True
    )[:top_n]
    
    # Calculate regional totals
    region_totals = _calculate_region_totals(country_list)
    
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
        countries_count=len(country_list),
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


def _build_country_list(
    gdp_by_country: Dict[str, MacroTimeSeries],
    pop_by_country: Dict[str, MacroTimeSeries],
    gdp_pc_by_country: Dict[str, MacroTimeSeries],
    fdi_in_by_country: Dict[str, MacroTimeSeries],
    fdi_out_by_country: Dict[str, MacroTimeSeries],
    exports_by_country: Dict[str, MacroTimeSeries],
    imports_by_country: Dict[str, MacroTimeSeries],
    country_by_code: Dict[str, CountryInfo],
    country_by_name: Dict[str, CountryInfo],
) -> List[CountryInfo]:
    """Build list of countries with all indicator data."""
    result = []
    
    for code, gdp_ts in gdp_by_country.items():
        latest_gdp = gdp_ts.get_latest()
        if not latest_gdp or not latest_gdp.value:
            continue
            
        # Find country metadata
        info = country_by_code.get(code)
        if not info:
            info = country_by_name.get(gdp_ts.country_name)
        
        # Get GDP growth
        gdp_growth = gdp_ts.get_growth_rate(latest_gdp.year)
        
        # Get population (optional)
        pop_ts = pop_by_country.get(code)
        pop_latest = pop_ts.get_latest() if pop_ts else None
        population = pop_latest.value if pop_latest else None
        pop_year = pop_latest.year if pop_latest else None
        
        # Get GDP per capita (optional)
        gdp_pc_ts = gdp_pc_by_country.get(code)
        gdp_pc_latest = gdp_pc_ts.get_latest() if gdp_pc_ts else None
        gdp_per_capita = gdp_pc_latest.value if gdp_pc_latest else None
        
        # Get FDI data (optional)
        fdi_in_ts = fdi_in_by_country.get(code)
        fdi_in_latest = fdi_in_ts.get_latest() if fdi_in_ts else None
        fdi_inflows = fdi_in_latest.value if fdi_in_latest else None
        
        fdi_out_ts = fdi_out_by_country.get(code)
        fdi_out_latest = fdi_out_ts.get_latest() if fdi_out_ts else None
        fdi_outflows = fdi_out_latest.value if fdi_out_latest else None
        
        # Calculate net FDI (inflows - outflows)
        fdi_net = None
        if fdi_inflows is not None and fdi_outflows is not None:
            fdi_net = fdi_inflows - fdi_outflows
        elif fdi_inflows is not None:
            fdi_net = fdi_inflows
        
        # Get trade data (optional)
        exp_ts = exports_by_country.get(code)
        exp_latest = exp_ts.get_latest() if exp_ts else None
        exports = exp_latest.value if exp_latest else None
        
        imp_ts = imports_by_country.get(code)
        imp_latest = imp_ts.get_latest() if imp_ts else None
        imports = imp_latest.value if imp_latest else None
        
        # Calculate trade balance
        trade_balance = None
        trade_balance_pct = None
        if exports is not None and imports is not None:
            trade_balance = exports - imports
            # Calculate trade balance as % of GDP
            if latest_gdp.value and latest_gdp.value > 0:
                trade_balance_pct = (trade_balance / latest_gdp.value) * 100
        
        if info:
            result.append(CountryInfo(
                code=code,
                name=info.name,
                region=info.region,
                income_level=info.income_level,
                capital=info.capital,
                latest_gdp=latest_gdp.value,
                latest_gdp_year=latest_gdp.year,
                gdp_growth=gdp_growth,
                gdp_per_capita=gdp_per_capita,
                population=population,
                population_year=pop_year,
                fdi_inflows=fdi_inflows,
                fdi_outflows=fdi_outflows,
                fdi_net=fdi_net,
                exports=exports,
                imports=imports,
                trade_balance=trade_balance,
                trade_balance_pct=trade_balance_pct,
            ))
        elif gdp_ts.country_name and len(code) <= 3:
            # Include without full metadata (filter aggregates)
            result.append(CountryInfo(
                code=code,
                name=gdp_ts.country_name,
                region="",
                income_level="",
                capital="",
                latest_gdp=latest_gdp.value,
                latest_gdp_year=latest_gdp.year,
                gdp_growth=gdp_growth,
                gdp_per_capita=gdp_per_capita,
                population=population,
                population_year=pop_year,
                fdi_inflows=fdi_inflows,
                fdi_outflows=fdi_outflows,
                fdi_net=fdi_net,
                exports=exports,
                imports=imports,
                trade_balance=trade_balance,
                trade_balance_pct=trade_balance_pct,
            ))
    
    return result


def _calculate_region_totals(countries: List[CountryInfo]) -> Dict[str, float]:
    """Calculate total GDP by region."""
    totals: Dict[str, float] = {}
    for c in countries:
        if c.region and c.latest_gdp:
            totals[c.region] = totals.get(c.region, 0) + c.latest_gdp
    return totals
