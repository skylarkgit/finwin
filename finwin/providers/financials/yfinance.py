"""Yahoo Finance data provider for finwin."""

from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, Optional

import yfinance as yf

from finwin.providers.base import (
    BaseProvider,
    ProviderResult,
    ProviderType,
    register_provider,
)

logger = logging.getLogger(__name__)

# Thread pool for running sync yfinance calls
_executor = ThreadPoolExecutor(max_workers=4)


def _fetch_yfinance_sync(symbol: str) -> Dict[str, Any]:
    """
    Synchronous yfinance data fetch.
    
    Runs in thread pool to avoid blocking.
    """
    data: Dict[str, Any] = {"symbol": symbol, "ok": False}
    
    try:
        t = yf.Ticker(symbol)
        info = t.info or {}
        
        data["info"] = info
        
        # Financials - convert Timestamp columns to strings
        try:
            fin = t.financials
            if fin is not None and not fin.empty:
                data["financials"] = fin.rename(columns=str).to_dict()
        except Exception:
            pass
        
        try:
            qfin = t.quarterly_financials
            if qfin is not None and not qfin.empty:
                data["quarterly_financials"] = qfin.rename(columns=str).to_dict()
        except Exception:
            pass
        
        try:
            bs = t.balance_sheet
            if bs is not None and not bs.empty:
                data["balance_sheet"] = bs.rename(columns=str).to_dict()
        except Exception:
            pass
        
        try:
            cf = t.cashflow
            if cf is not None and not cf.empty:
                data["cashflow"] = cf.rename(columns=str).to_dict()
        except Exception:
            pass
        
        data["ok"] = True
        
    except Exception as e:
        data["error"] = str(e)
        logger.exception(f"yfinance error for {symbol}: {e}")
    
    return data


@register_provider("yfinance")
class YFinanceProvider(BaseProvider):
    """
    Fetches financial data from Yahoo Finance.
    
    Note: yfinance is synchronous, so we run it in a thread pool.
    """
    
    name = "yfinance"
    provider_type = ProviderType.FINANCIALS
    supports_symbol = True
    supports_query = False  # yfinance requires a symbol
    
    def __init__(self):
        pass
    
    async def gather(
        self,
        symbol: Optional[str] = None,
        query: Optional[str] = None,
        **kwargs: Any,
    ) -> ProviderResult:
        """
        Gather financial data from Yahoo Finance.
        
        Args:
            symbol: Stock symbol (required, e.g., "TCS.NS", "AAPL")
            query: Not used for this provider
            **kwargs: Additional arguments
            
        Returns:
            ProviderResult with financial data
        """
        if not symbol:
            return ProviderResult(
                provider_name=self.name,
                provider_type=self.provider_type,
                success=False,
                error="No symbol provided",
            )
        
        try:
            # Run sync yfinance in thread pool
            loop = asyncio.get_event_loop()
            raw_data = await loop.run_in_executor(
                _executor,
                _fetch_yfinance_sync,
                symbol,
            )
            
            if not raw_data.get("ok"):
                return ProviderResult(
                    provider_name=self.name,
                    provider_type=self.provider_type,
                    success=False,
                    error=raw_data.get("error", "Unknown error"),
                )
            
            info = raw_data.get("info", {})
            
            # Build structured financials data
            financials = {
                "symbol": symbol,
                "ok": True,
                "short_name": info.get("shortName"),
                "long_name": info.get("longName"),
                "sector": info.get("sector"),
                "industry": info.get("industry"),
                "website": info.get("website"),
                "market_cap": info.get("marketCap"),
                "currency": info.get("currency"),
                "exchange": info.get("exchange"),
                "quote_type": info.get("quoteType"),
                "trailing_pe": info.get("trailingPE"),
                "forward_pe": info.get("forwardPE"),
                "price_to_book": info.get("priceToBook"),
                "current_price": info.get("currentPrice"),
                "previous_close": info.get("previousClose"),
                "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
                "fifty_two_week_low": info.get("fiftyTwoWeekLow"),
                "beta": info.get("beta"),
                "dividend_yield": info.get("dividendYield"),
                "raw_financials": raw_data.get("financials"),
                "raw_quarterly_financials": raw_data.get("quarterly_financials"),
                "raw_balance_sheet": raw_data.get("balance_sheet"),
                "raw_cashflow": raw_data.get("cashflow"),
            }
            
            # Build raw text for LLM context
            raw_texts = []
            name = info.get("longName") or info.get("shortName") or symbol
            price = info.get("currentPrice")
            currency = info.get("currency", "USD")
            market_cap = info.get("marketCap")
            
            summary_parts = [f"Company: {name} ({symbol})"]
            if price:
                summary_parts.append(f"Current Price: {currency} {price}")
            if market_cap:
                summary_parts.append(f"Market Cap: {market_cap:,.0f}")
            if info.get("sector"):
                summary_parts.append(f"Sector: {info.get('sector')}")
            if info.get("industry"):
                summary_parts.append(f"Industry: {info.get('industry')}")
            if info.get("trailingPE"):
                summary_parts.append(f"P/E (TTM): {info.get('trailingPE'):.2f}")
            
            raw_texts.append("\n".join(summary_parts))
            
            return ProviderResult(
                provider_name=self.name,
                provider_type=self.provider_type,
                success=True,
                data={
                    "financials": financials,
                    "raw_info": info,
                },
                raw_texts=raw_texts,
                metadata={
                    "symbol": symbol,
                    "exchange": info.get("exchange"),
                },
            )
            
        except Exception as e:
            logger.exception(f"Failed to gather financials: {e}")
            return ProviderResult(
                provider_name=self.name,
                provider_type=self.provider_type,
                success=False,
                error=str(e),
            )
    
    def get_tool_description(self) -> str:
        """Get description for LLM tool use."""
        return (
            "Fetch financial data for a stock symbol from Yahoo Finance. "
            "Returns price, market cap, P/E ratios, sector, industry, "
            "and detailed financial statements."
        )
