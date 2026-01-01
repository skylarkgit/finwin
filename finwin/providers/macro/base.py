"""Base class for macroeconomic data providers."""

from __future__ import annotations

from abc import abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

from finwin.providers.base import BaseProvider, ProviderResult, ProviderType
from finwin.models.macro import (
    MacroTimeSeries,
    MacroDataPoint,
    CountryInfo,
    MacroIndicatorInfo,
    DataFrequency,
)


class BaseMacroProvider(BaseProvider):
    """
    Abstract base class for macroeconomic data providers.
    
    Macro providers fetch time series data for indicators like GDP,
    inflation, unemployment across countries.
    
    Key differences from BaseProvider:
    - Uses country codes instead of stock symbols
    - Returns time series data instead of point-in-time
    - Supports indicator-based queries
    """
    
    name: str = "macro_base"
    provider_type: ProviderType = ProviderType.MACRO
    
    # Macro-specific capabilities
    supports_symbol: bool = False  # Use country codes instead
    supports_query: bool = False
    supports_batch: bool = True  # Most macro APIs support batch requests
    
    # Provider-specific
    supported_indicators: List[str] = []
    supported_countries: List[str] = []
    
    @abstractmethod
    async def get_indicator(
        self,
        indicator: str,
        country: Optional[str] = None,
        start_year: Optional[int] = None,
        end_year: Optional[int] = None,
    ) -> MacroTimeSeries:
        """
        Get time series data for a specific indicator.
        
        Args:
            indicator: Indicator ID (e.g., "gdp", "gdp_growth")
            country: ISO country code (None = world/all)
            start_year: Start year for data
            end_year: End year for data
            
        Returns:
            MacroTimeSeries with the data
        """
        pass
    
    @abstractmethod
    async def get_countries(self) -> List[CountryInfo]:
        """Get list of available countries."""
        pass
    
    @abstractmethod
    async def get_indicators(self) -> List[MacroIndicatorInfo]:
        """Get list of available indicators."""
        pass
    
    async def get_gdp_all_countries(
        self,
        start_year: Optional[int] = None,
        end_year: Optional[int] = None,
    ) -> Dict[str, MacroTimeSeries]:
        """
        Get GDP data for all available countries.
        
        Returns:
            Dict mapping country code to MacroTimeSeries
        """
        # Default implementation - override for efficiency
        countries = await self.get_countries()
        result = {}
        
        for country in countries:
            try:
                ts = await self.get_indicator(
                    indicator="gdp",
                    country=country.code,
                    start_year=start_year,
                    end_year=end_year,
                )
                result[country.code] = ts
            except Exception:
                # Skip countries with no data
                continue
        
        return result
    
    async def gather(
        self,
        symbol: Optional[str] = None,
        query: Optional[str] = None,
        **kwargs: Any,
    ) -> ProviderResult:
        """
        Gather macro data (implements BaseProvider interface).
        
        For macro providers, use:
        - symbol as country code
        - query as indicator name
        - kwargs for start_year, end_year
        """
        country = symbol or kwargs.get("country")
        indicator = query or kwargs.get("indicator", "gdp")
        start_year = kwargs.get("start_year")
        end_year = kwargs.get("end_year")
        
        try:
            ts = await self.get_indicator(
                indicator=indicator,
                country=country,
                start_year=start_year,
                end_year=end_year,
            )
            
            # Convert to ProviderResult
            return ProviderResult(
                provider_name=self.name,
                provider_type=self.provider_type,
                success=True,
                data={
                    "indicator": indicator,
                    "country": country,
                    "time_series": ts.model_dump(),
                },
                raw_texts=[self._format_for_llm(ts)],
                metadata={
                    "start_year": start_year,
                    "end_year": end_year,
                    "data_points": len(ts.data),
                },
            )
        except Exception as e:
            return ProviderResult(
                provider_name=self.name,
                provider_type=self.provider_type,
                success=False,
                error=str(e),
            )
    
    def _format_for_llm(self, ts: MacroTimeSeries) -> str:
        """Format time series data for LLM context."""
        lines = [
            f"## {ts.indicator_name} - {ts.country_name}",
            f"Source: {ts.source}",
            f"Unit: {ts.unit} ({ts.scale})",
            "",
            "| Year | Value |",
            "|------|-------|",
        ]
        
        for dp in sorted(ts.data, key=lambda x: x.year, reverse=True)[:10]:
            if dp.value is not None:
                # Format large numbers
                if abs(dp.value) >= 1e12:
                    formatted = f"${dp.value/1e12:.2f}T"
                elif abs(dp.value) >= 1e9:
                    formatted = f"${dp.value/1e9:.2f}B"
                elif abs(dp.value) >= 1e6:
                    formatted = f"${dp.value/1e6:.2f}M"
                else:
                    formatted = f"{dp.value:.2f}"
                lines.append(f"| {dp.year} | {formatted} |")
        
        return "\n".join(lines)
    
    def get_tool_description(self) -> str:
        """Get description for LLM tool use."""
        return (
            f"{self.name} - Macroeconomic data provider. "
            f"Supports indicators: {', '.join(self.supported_indicators[:5])}..."
        )
    
    def get_tool_parameters(self) -> Dict[str, Any]:
        """Get parameter schema for LLM tool use."""
        current_year = datetime.now().year
        return {
            "type": "object",
            "properties": {
                "indicator": {
                    "type": "string",
                    "description": "Indicator ID (gdp, gdp_growth, gdp_per_capita)",
                    "enum": self.supported_indicators or ["gdp"],
                },
                "country": {
                    "type": "string",
                    "description": "ISO country code (US, IN, CN) or None for world",
                },
                "start_year": {
                    "type": "integer",
                    "description": "Start year for data range",
                    "default": current_year - 20,
                },
                "end_year": {
                    "type": "integer",
                    "description": "End year for data range",
                    "default": current_year,
                },
            },
            "required": ["indicator"],
        }
