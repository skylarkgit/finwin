"""World Bank data provider for macroeconomic indicators."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

from finwin.providers.base import register_provider
from finwin.providers.macro.base import BaseMacroProvider
from finwin.models.macro import (
    MacroTimeSeries,
    MacroDataPoint,
    CountryInfo,
    MacroIndicatorInfo,
    DataFrequency,
)
from finwin.cache import get_cache, cached


# World Bank indicator codes
INDICATOR_CODES = {
    "gdp": "NY.GDP.MKTP.CD",           # GDP (current US$)
    "gdp_growth": "NY.GDP.MKTP.KD.ZG", # GDP growth (annual %)
    "gdp_per_capita": "NY.GDP.PCAP.CD", # GDP per capita (current US$)
    "inflation": "FP.CPI.TOTL.ZG",      # Inflation, consumer prices
    "unemployment": "SL.UEM.TOTL.ZS",   # Unemployment, total (% of labor)
    "population": "SP.POP.TOTL",        # Population, total
}

INDICATOR_INFO = {
    "gdp": MacroIndicatorInfo(
        id="gdp",
        name="GDP (current US$)",
        description="Gross Domestic Product in current US dollars",
        unit="USD",
        source="World Bank",
        worldbank_code="NY.GDP.MKTP.CD",
    ),
    "gdp_growth": MacroIndicatorInfo(
        id="gdp_growth",
        name="GDP Growth (annual %)",
        description="Annual percentage growth rate of GDP",
        unit="percent",
        source="World Bank",
        worldbank_code="NY.GDP.MKTP.KD.ZG",
    ),
    "gdp_per_capita": MacroIndicatorInfo(
        id="gdp_per_capita",
        name="GDP per capita (current US$)",
        description="GDP divided by midyear population",
        unit="USD",
        source="World Bank",
        worldbank_code="NY.GDP.PCAP.CD",
    ),
}


@register_provider("worldbank")
class WorldBankProvider(BaseMacroProvider):
    """
    World Bank Open Data API provider.
    
    Free access to GDP, inflation, population, and other
    development indicators for 200+ countries.
    
    API docs: https://datahelpdesk.worldbank.org/knowledgebase/topics/125589
    
    No API key required.
    """
    
    name: str = "worldbank"
    supported_indicators: List[str] = list(INDICATOR_CODES.keys())
    
    BASE_URL = "https://api.worldbank.org/v2"
    
    def __init__(
        self,
        timeout: int = 30,
        cache_ttl: int = 604800,  # 7 days
    ):
        """
        Initialize World Bank provider.
        
        Args:
            timeout: HTTP request timeout in seconds
            cache_ttl: Cache TTL in seconds (default 7 days)
        """
        self.timeout = timeout
        self.cache_ttl = cache_ttl
        self._client: Optional[httpx.AsyncClient] = None
        self._cache = get_cache()
        self._countries_cache: Optional[List[CountryInfo]] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True,
            )
        return self._client
    
    async def close(self) -> None:
        """Close HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
    
    async def _fetch_indicator(
        self,
        indicator_code: str,
        country: str = "all",
        start_year: Optional[int] = None,
        end_year: Optional[int] = None,
        per_page: int = 1000,
    ) -> List[Dict[str, Any]]:
        """
        Fetch raw indicator data from World Bank API.
        
        Returns list of data points from the API.
        """
        # Build cache key
        cache_key = f"wb:{indicator_code}:{country}:{start_year}:{end_year}"
        
        # Check cache
        cached_data = await self._cache.get(cache_key)
        if cached_data is not None:
            return cached_data
        
        # Build URL
        current_year = datetime.now().year
        start = start_year or (current_year - 20)
        end = end_year or current_year
        
        url = (
            f"{self.BASE_URL}/country/{country}/indicator/{indicator_code}"
            f"?format=json&per_page={per_page}&date={start}:{end}"
        )
        
        client = await self._get_client()
        
        try:
            response = await client.get(url)
            response.raise_for_status()
            
            data = response.json()
            
            # World Bank returns [metadata, data] or just metadata on error
            if not isinstance(data, list) or len(data) < 2:
                return []
            
            result = data[1] or []
            
            # Cache the result
            await self._cache.set(cache_key, result, ttl=self.cache_ttl)
            
            return result
            
        except httpx.HTTPError as e:
            raise RuntimeError(f"World Bank API error: {e}")
    
    async def get_indicator(
        self,
        indicator: str,
        country: Optional[str] = None,
        start_year: Optional[int] = None,
        end_year: Optional[int] = None,
    ) -> MacroTimeSeries:
        """Get time series data for an indicator."""
        # Map indicator name to World Bank code
        indicator_code = INDICATOR_CODES.get(indicator)
        if not indicator_code:
            raise ValueError(f"Unknown indicator: {indicator}")
        
        # Default to world data
        country_code = country or "WLD"
        
        # Fetch data
        raw_data = await self._fetch_indicator(
            indicator_code=indicator_code,
            country=country_code,
            start_year=start_year,
            end_year=end_year,
        )
        
        # Parse response
        data_points = []
        country_name = ""
        
        for item in raw_data:
            if item is None:
                continue
                
            year = int(item.get("date", 0))
            value = item.get("value")
            
            if not country_name and item.get("country"):
                country_name = item["country"].get("value", "")
            
            data_points.append(MacroDataPoint(
                date=str(year),
                year=year,
                value=float(value) if value is not None else None,
            ))
        
        # Get indicator info
        info = INDICATOR_INFO.get(indicator, MacroIndicatorInfo(
            id=indicator,
            name=indicator,
        ))
        
        return MacroTimeSeries(
            indicator_id=indicator,
            indicator_name=info.name,
            country_code=country_code,
            country_name=country_name or country_code,
            data=data_points,
            unit=info.unit,
            scale="current" if "current" in info.name.lower() else "",
            frequency=DataFrequency.ANNUAL,
            source="World Bank",
        )
    
    async def get_countries(self) -> List[CountryInfo]:
        """Get list of available countries."""
        # Check cache
        if self._countries_cache is not None:
            return self._countries_cache
        
        cache_key = "wb:countries"
        cached = await self._cache.get(cache_key)
        if cached is not None:
            self._countries_cache = [CountryInfo(**c) for c in cached]
            return self._countries_cache
        
        # Fetch from API
        url = f"{self.BASE_URL}/country?format=json&per_page=500"
        
        client = await self._get_client()
        
        try:
            response = await client.get(url)
            response.raise_for_status()
            
            data = response.json()
            
            if not isinstance(data, list) or len(data) < 2:
                return []
            
            countries = []
            for item in (data[1] or []):
                # Skip aggregates (they have no capitalCity)
                if not item.get("capitalCity"):
                    continue
                    
                countries.append(CountryInfo(
                    code=item.get("id", ""),
                    name=item.get("name", ""),
                    region=item.get("region", {}).get("value", ""),
                    income_level=item.get("incomeLevel", {}).get("value", ""),
                    capital=item.get("capitalCity", ""),
                ))
            
            # Cache
            await self._cache.set(
                cache_key,
                [c.model_dump() for c in countries],
                ttl=2592000,  # 30 days
            )
            
            self._countries_cache = countries
            return countries
            
        except httpx.HTTPError as e:
            raise RuntimeError(f"World Bank API error: {e}")
    
    async def get_indicators(self) -> List[MacroIndicatorInfo]:
        """Get list of available indicators."""
        return list(INDICATOR_INFO.values())
    
    async def get_gdp_all_countries(
        self,
        start_year: Optional[int] = None,
        end_year: Optional[int] = None,
    ) -> Dict[str, MacroTimeSeries]:
        """
        Get GDP data for all countries efficiently.
        
        Uses batch API call instead of per-country.
        """
        # Fetch all GDP data in one call
        raw_data = await self._fetch_indicator(
            indicator_code=INDICATOR_CODES["gdp"],
            country="all",
            start_year=start_year,
            end_year=end_year,
            per_page=20000,  # Get all data
        )
        
        # Group by country
        by_country: Dict[str, List[MacroDataPoint]] = {}
        country_names: Dict[str, str] = {}
        
        for item in raw_data:
            if item is None:
                continue
            
            country_info = item.get("country", {})
            country_code = country_info.get("id", "")
            country_name = country_info.get("value", "")
            
            if not country_code:
                continue
            
            country_names[country_code] = country_name
            
            year = int(item.get("date", 0))
            value = item.get("value")
            
            if country_code not in by_country:
                by_country[country_code] = []
            
            by_country[country_code].append(MacroDataPoint(
                date=str(year),
                year=year,
                value=float(value) if value is not None else None,
            ))
        
        # Convert to MacroTimeSeries
        result = {}
        info = INDICATOR_INFO["gdp"]
        
        for code, data_points in by_country.items():
            result[code] = MacroTimeSeries(
                indicator_id="gdp",
                indicator_name=info.name,
                country_code=code,
                country_name=country_names.get(code, code),
                data=data_points,
                unit=info.unit,
                scale="current",
                frequency=DataFrequency.ANNUAL,
                source="World Bank",
            )
        
        return result
    
    def get_tool_description(self) -> str:
        """Get description for LLM tool use."""
        return (
            "World Bank Open Data - Access GDP, inflation, population "
            "and development indicators for 200+ countries. "
            "Data from 1960 to present."
        )
