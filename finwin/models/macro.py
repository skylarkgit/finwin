"""Macroeconomic data models for finwin."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class MacroIndicatorType(str, Enum):
    """Types of macroeconomic indicators."""
    
    GDP = "gdp"
    GDP_GROWTH = "gdp_growth"
    GDP_PER_CAPITA = "gdp_per_capita"
    INFLATION = "inflation"
    UNEMPLOYMENT = "unemployment"
    INTEREST_RATE = "interest_rate"
    TRADE_BALANCE = "trade_balance"
    CURRENT_ACCOUNT = "current_account"
    DEBT_TO_GDP = "debt_to_gdp"
    POPULATION = "population"


class DataFrequency(str, Enum):
    """Data frequency/granularity."""
    
    ANNUAL = "annual"
    QUARTERLY = "quarterly"
    MONTHLY = "monthly"
    WEEKLY = "weekly"
    DAILY = "daily"


class MacroDataPoint(BaseModel):
    """Single data point in a macroeconomic time series."""
    
    date: str  # ISO format date string (YYYY or YYYY-MM-DD)
    year: int
    value: Optional[float] = None
    
    # Optional metadata
    is_estimate: bool = False
    is_forecast: bool = False


class MacroTimeSeries(BaseModel):
    """Time series data for a macroeconomic indicator."""
    
    indicator_id: str
    indicator_name: str
    country_code: str
    country_name: str
    
    # Data
    data: List[MacroDataPoint] = Field(default_factory=list)
    
    # Metadata
    unit: str = ""  # e.g., "USD", "percent", "index"
    scale: str = ""  # e.g., "billions", "millions"
    frequency: DataFrequency = DataFrequency.ANNUAL
    source: str = ""
    last_updated: Optional[str] = None
    
    def get_latest(self) -> Optional[MacroDataPoint]:
        """Get the most recent data point."""
        if not self.data:
            return None
        # Sort by year descending and get first non-null value
        sorted_data = sorted(
            [d for d in self.data if d.value is not None],
            key=lambda x: x.year,
            reverse=True,
        )
        return sorted_data[0] if sorted_data else None
    
    def get_values_dict(self) -> Dict[int, Optional[float]]:
        """Get data as year -> value dict."""
        return {d.year: d.value for d in self.data}
    
    def get_growth_rate(self, year: int) -> Optional[float]:
        """Calculate year-over-year growth rate."""
        values = self.get_values_dict()
        current = values.get(year)
        previous = values.get(year - 1)
        
        if current is None or previous is None or previous == 0:
            return None
        
        return ((current - previous) / abs(previous)) * 100


class CountryInfo(BaseModel):
    """Information about a country with key economic indicators."""
    
    code: str  # ISO 3166-1 alpha-2 or alpha-3
    name: str
    region: str = ""
    income_level: str = ""
    capital: str = ""
    
    # GDP indicators
    latest_gdp: Optional[float] = None
    latest_gdp_year: Optional[int] = None
    gdp_growth: Optional[float] = None
    gdp_per_capita: Optional[float] = None
    
    # Population
    population: Optional[float] = None
    population_year: Optional[int] = None
    
    # FDI (Foreign Direct Investment)
    fdi_inflows: Optional[float] = None  # Net inflows in current USD
    fdi_outflows: Optional[float] = None  # Net outflows in current USD
    fdi_net: Optional[float] = None  # Net FDI (inflows - outflows)
    
    # Trade
    exports: Optional[float] = None  # Exports of goods & services (USD)
    imports: Optional[float] = None  # Imports of goods & services (USD)
    trade_balance: Optional[float] = None  # Exports - Imports
    trade_balance_pct: Optional[float] = None  # Trade balance as % of GDP
    
    # Other key metrics
    inflation: Optional[float] = None
    unemployment: Optional[float] = None


class MacroIndicatorInfo(BaseModel):
    """Information about an available indicator."""
    
    id: str
    name: str
    description: str = ""
    unit: str = ""
    source: str = ""
    
    # API-specific codes
    worldbank_code: Optional[str] = None
    fred_code: Optional[str] = None
    imf_code: Optional[str] = None


class GlobalGDPSummary(BaseModel):
    """Summary of global GDP data for dashboard."""
    
    # World totals
    world_gdp_total: Optional[float] = None  # Current USD
    world_gdp_year: Optional[int] = None
    world_gdp_growth: Optional[float] = None
    
    # Historical world GDP
    world_gdp_history: List[MacroDataPoint] = Field(default_factory=list)
    
    # Top economies
    top_countries: List[CountryInfo] = Field(default_factory=list)
    
    # Regional breakdown
    region_totals: Dict[str, float] = Field(default_factory=dict)
    
    # Metadata
    data_source: str = "World Bank"
    last_updated: Optional[str] = None
    countries_count: int = 0


class MacroDashboardData(BaseModel):
    """Complete data for the macro dashboard."""
    
    # GDP data
    gdp_summary: GlobalGDPSummary = Field(default_factory=GlobalGDPSummary)
    
    # Available countries
    countries: List[CountryInfo] = Field(default_factory=list)
    
    # GDP by country (for charts)
    gdp_by_country: Dict[str, MacroTimeSeries] = Field(default_factory=dict)
    
    # Metadata
    generated_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat()
    )
    cache_ttl: int = 86400  # seconds
