import type { Financials } from '../types';

interface FinancialsCardProps {
  financials: Financials;
}

function formatNumber(value: number | null, decimals: number = 2): string {
  if (value === null || value === undefined) return '—';
  return value.toLocaleString(undefined, { 
    minimumFractionDigits: decimals, 
    maximumFractionDigits: decimals 
  });
}

function formatMarketCap(value: number | null): string {
  if (value === null || value === undefined) return '—';
  if (value >= 1e12) return `${(value / 1e12).toFixed(2)}T`;
  if (value >= 1e9) return `${(value / 1e9).toFixed(2)}B`;
  if (value >= 1e6) return `${(value / 1e6).toFixed(2)}M`;
  return formatNumber(value, 0);
}

function formatPercent(value: number | null): string {
  if (value === null || value === undefined) return '—';
  return `${(value * 100).toFixed(2)}%`;
}

export function FinancialsCard({ financials }: FinancialsCardProps) {
  if (!financials.ok) {
    return (
      <div className="card financials-card error">
        <h3>Financials</h3>
        <p className="error-message">
          {financials.error || 'Failed to load financials'}
        </p>
      </div>
    );
  }

  return (
    <div className="card financials-card">
      <div className="card-header">
        <h3>{financials.long_name || financials.short_name || financials.symbol}</h3>
        {financials.sector && financials.industry && (
          <span className="sector-badge">
            {financials.sector} · {financials.industry}
          </span>
        )}
      </div>
      
      <div className="price-section">
        <div className="current-price">
          <span className="currency">{financials.currency || '$'}</span>
          <span className="price">{formatNumber(financials.current_price)}</span>
        </div>
        {financials.previous_close && (
          <span className={`price-change ${
            financials.current_price && financials.current_price > financials.previous_close 
              ? 'positive' 
              : 'negative'
          }`}>
            {financials.current_price && (
              <>
                {financials.current_price > financials.previous_close ? '▲' : '▼'}{' '}
                {formatNumber(financials.current_price - financials.previous_close)} (
                {formatPercent((financials.current_price - financials.previous_close) / financials.previous_close)})
              </>
            )}
          </span>
        )}
      </div>

      <div className="metrics-grid">
        <div className="metric">
          <span className="metric-label">Market Cap</span>
          <span className="metric-value">{formatMarketCap(financials.market_cap)}</span>
        </div>
        <div className="metric">
          <span className="metric-label">P/E (TTM)</span>
          <span className="metric-value">{formatNumber(financials.trailing_pe)}</span>
        </div>
        <div className="metric">
          <span className="metric-label">P/E (FWD)</span>
          <span className="metric-value">{formatNumber(financials.forward_pe)}</span>
        </div>
        <div className="metric">
          <span className="metric-label">P/B</span>
          <span className="metric-value">{formatNumber(financials.price_to_book)}</span>
        </div>
        <div className="metric">
          <span className="metric-label">52W High</span>
          <span className="metric-value">{formatNumber(financials.fifty_two_week_high)}</span>
        </div>
        <div className="metric">
          <span className="metric-label">52W Low</span>
          <span className="metric-value">{formatNumber(financials.fifty_two_week_low)}</span>
        </div>
        <div className="metric">
          <span className="metric-label">Beta</span>
          <span className="metric-value">{formatNumber(financials.beta)}</span>
        </div>
        <div className="metric">
          <span className="metric-label">Div Yield</span>
          <span className="metric-value">{formatPercent(financials.dividend_yield)}</span>
        </div>
      </div>

      {financials.website && (
        <a href={financials.website} target="_blank" rel="noopener noreferrer" className="website-link">
          {financials.website.replace(/^https?:\/\//, '').replace(/\/$/, '')}
        </a>
      )}
    </div>
  );
}
