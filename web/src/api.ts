import type { StockContext } from './types';

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
