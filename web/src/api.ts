import type { 
  StockContext, 
  MacroDashboardData, 
  MacroTimeSeries,
  CountryInfo,
  MacroIndicatorInfo 
} from './types';

const API_BASE = 'http://localhost:8000';

export async function fetchContext(
  symbol?: string,
  query?: string,
  newsCount: number = 10
): Promise<StockContext> {
  const params = new URLSearchParams();
  if (symbol) params.append('symbol', symbol);
  if (query) params.append('query', query);
  params.append('news_count', newsCount.toString());

  const response = await fetch(`${API_BASE}/api/context?${params}`);
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to fetch context');
  }
  
  return response.json();
}

export async function healthCheck(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE}/health`);
    return response.ok;
  } catch {
    return false;
  }
}

// =============================================================================
// Macro Dashboard API
// =============================================================================

export async function fetchMacroDashboard(
  startYear?: number,
  endYear?: number,
  topN: number = 20
): Promise<MacroDashboardData> {
  const params = new URLSearchParams();
  if (startYear) params.append('start_year', startYear.toString());
  if (endYear) params.append('end_year', endYear.toString());
  params.append('top_n', topN.toString());

  const response = await fetch(`${API_BASE}/api/macro/dashboard?${params}`);
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to fetch macro dashboard');
  }
  
  return response.json();
}

export async function fetchCountryGDP(
  country: string,
  startYear?: number,
  endYear?: number
): Promise<MacroTimeSeries> {
  const params = new URLSearchParams();
  if (startYear) params.append('start_year', startYear.toString());
  if (endYear) params.append('end_year', endYear.toString());

  const response = await fetch(`${API_BASE}/api/macro/gdp/${country}?${params}`);
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || `Failed to fetch GDP for ${country}`);
  }
  
  return response.json();
}

export async function fetchMacroIndicator(
  indicator: string,
  country: string,
  startYear?: number,
  endYear?: number
): Promise<MacroTimeSeries> {
  const params = new URLSearchParams();
  if (startYear) params.append('start_year', startYear.toString());
  if (endYear) params.append('end_year', endYear.toString());

  const response = await fetch(
    `${API_BASE}/api/macro/indicator/${indicator}/${country}?${params}`
  );
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || `Failed to fetch ${indicator} for ${country}`);
  }
  
  return response.json();
}

export async function fetchMacroCountries(): Promise<CountryInfo[]> {
  const response = await fetch(`${API_BASE}/api/macro/countries`);
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to fetch countries');
  }
  
  return response.json();
}

export async function fetchMacroIndicators(): Promise<MacroIndicatorInfo[]> {
  const response = await fetch(`${API_BASE}/api/macro/indicators`);
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to fetch indicators');
  }
  
  return response.json();
}

// Utility functions for formatting
export function formatGDP(value: number | null): string {
  if (value === null) return 'N/A';
  
  if (Math.abs(value) >= 1e12) {
    return `$${(value / 1e12).toFixed(2)}T`;
  } else if (Math.abs(value) >= 1e9) {
    return `$${(value / 1e9).toFixed(2)}B`;
  } else if (Math.abs(value) >= 1e6) {
    return `$${(value / 1e6).toFixed(2)}M`;
  } else {
    return `$${value.toFixed(0)}`;
  }
}

export function formatGrowth(value: number | null): string {
  if (value === null) return 'N/A';
  const sign = value >= 0 ? '+' : '';
  return `${sign}${value.toFixed(2)}%`;
}

export function formatPopulation(value: number | null): string {
  if (value === null) return 'N/A';
  
  if (value >= 1e9) {
    return `${(value / 1e9).toFixed(2)}B`;
  } else if (value >= 1e6) {
    return `${(value / 1e6).toFixed(1)}M`;
  } else if (value >= 1e3) {
    return `${(value / 1e3).toFixed(0)}K`;
  } else {
    return value.toFixed(0);
  }
}

export function formatGDPPerCapita(value: number | null): string {
  if (value === null) return 'N/A';
  return `$${value.toLocaleString('en-US', { maximumFractionDigits: 0 })}`;
}

export function formatPercent(value: number | null): string {
  if (value === null) return 'N/A';
  return `${value.toFixed(1)}%`;
}
