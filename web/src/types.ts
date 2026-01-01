// TypeScript types matching our Pydantic models

export interface NewsArticle {
  title: string;
  link: string;
  resolved_link: string | null;
  published: string | null;
  source: string | null;
  extracted_text: string | null;
}

export interface FetchResult {
  url: string;
  resolved_url: string | null;
  status: number;
  content_type: string;
  extracted_text: string | null;
  error: string | null;
}

export interface Financials {
  symbol: string;
  ok: boolean;
  error: string | null;
  short_name: string | null;
  long_name: string | null;
  sector: string | null;
  industry: string | null;
  website: string | null;
  market_cap: number | null;
  currency: string | null;
  exchange: string | null;
  quote_type: string | null;
  trailing_pe: number | null;
  forward_pe: number | null;
  price_to_book: number | null;
  current_price: number | null;
  previous_close: number | null;
  fifty_two_week_high: number | null;
  fifty_two_week_low: number | null;
  beta: number | null;
  dividend_yield: number | null;
  raw_financials: Record<string, unknown> | null;
  raw_quarterly_financials: Record<string, unknown> | null;
  raw_balance_sheet: Record<string, unknown> | null;
  raw_cashflow: Record<string, unknown> | null;
}

export interface SourceResult {
  name: string;
  success: boolean;
  error: string | null;
  data: Record<string, unknown>;
  raw_texts: string[];
}

export interface Meta {
  label: string;
  symbol: string | null;
  query: string | null;
  generated_at_utc: string;
}

export interface StockContext {
  meta: Meta;
  financials: Financials | null;
  news: NewsArticle[];
  fetches: FetchResult[];
  source_results: SourceResult[];
  all_texts: string[];
}

// =============================================================================
// Macro Dashboard Types
// =============================================================================

export interface MacroDataPoint {
  date: string;
  year: number;
  value: number | null;
  is_estimate?: boolean;
  is_forecast?: boolean;
}

export interface MacroTimeSeries {
  indicator_id: string;
  indicator_name: string;
  country_code: string;
  country_name: string;
  data: MacroDataPoint[];
  unit: string;
  scale: string;
  frequency: string;
  source: string;
  last_updated: string | null;
}

export interface CountryInfo {
  code: string;
  name: string;
  region: string;
  income_level: string;
  capital: string;
  latest_gdp: number | null;
  latest_gdp_year: number | null;
  gdp_growth: number | null;
  gdp_per_capita: number | null;
  population: number | null;
  population_year: number | null;
  inflation: number | null;
  unemployment: number | null;
}

export interface MacroIndicatorInfo {
  id: string;
  name: string;
  description: string;
  unit: string;
  source: string;
  worldbank_code: string | null;
  fred_code: string | null;
  imf_code: string | null;
}

export interface GlobalGDPSummary {
  world_gdp_total: number | null;
  world_gdp_year: number | null;
  world_gdp_growth: number | null;
  world_gdp_history: MacroDataPoint[];
  top_countries: CountryInfo[];
  region_totals: Record<string, number>;
  data_source: string;
  last_updated: string | null;
  countries_count: number;
}

export interface MacroDashboardData {
  gdp_summary: GlobalGDPSummary;
  countries: CountryInfo[];
  gdp_by_country: Record<string, MacroTimeSeries>;
  generated_at: string;
  cache_ttl: number;
}
