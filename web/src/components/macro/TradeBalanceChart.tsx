import type { CountryInfo } from '../../types';
import { formatTradeBalance, formatGDP } from '../../api';

interface TradeBalanceChartProps {
  countries: CountryInfo[];
  limit?: number;
}

export function TradeBalanceChart({ countries, limit = 20 }: TradeBalanceChartProps) {
  // Get countries with trade data, filter to actual countries only
  const countriesWithTrade = countries
    .filter(c => c.trade_balance !== null && c.region)
    .sort((a, b) => (b.trade_balance ?? 0) - (a.trade_balance ?? 0));

  if (countriesWithTrade.length === 0) {
    return <div className="no-data">No trade data available</div>;
  }

  // Get top surplus and deficit countries
  const topSurplus = countriesWithTrade.filter(c => (c.trade_balance ?? 0) > 0).slice(0, limit / 2);
  const topDeficit = countriesWithTrade.filter(c => (c.trade_balance ?? 0) < 0).slice(-(limit / 2)).reverse();
  
  const displayCountries = [...topSurplus, ...topDeficit];
  
  // Find max absolute value for scaling
  const maxAbsValue = Math.max(
    ...displayCountries.map(c => Math.abs(c.trade_balance ?? 0))
  );

  return (
    <div className="trade-balance-chart">
      <div className="chart-legend">
        <span className="legend-item surplus">
          <span className="color-box"></span> Trade Surplus (Exports &gt; Imports)
        </span>
        <span className="legend-item deficit">
          <span className="color-box"></span> Trade Deficit (Imports &gt; Exports)
        </span>
      </div>
      
      <div className="trade-bars">
        {displayCountries.map((country) => {
          const balance = country.trade_balance ?? 0;
          const isSurplus = balance >= 0;
          const barWidth = maxAbsValue > 0 ? (Math.abs(balance) / maxAbsValue) * 100 : 0;
          
          return (
            <div key={country.code} className="trade-bar-row">
              <div className="country-label">
                <span className="code">{country.code}</span>
                <span className="name">{country.name}</span>
              </div>
              
              <div className="diverging-bar-container">
                <div className="left-side">
                  {!isSurplus && (
                    <div 
                      className="bar deficit"
                      style={{ width: `${barWidth}%` }}
                      title={`Exports: ${formatGDP(country.exports)}, Imports: ${formatGDP(country.imports)}`}
                    />
                  )}
                </div>
                <div className="center-line" />
                <div className="right-side">
                  {isSurplus && (
                    <div 
                      className="bar surplus"
                      style={{ width: `${barWidth}%` }}
                      title={`Exports: ${formatGDP(country.exports)}, Imports: ${formatGDP(country.imports)}`}
                    />
                  )}
                </div>
              </div>
              
              <div className={`value ${isSurplus ? 'surplus' : 'deficit'}`}>
                {formatTradeBalance(balance)}
              </div>
            </div>
          );
        })}
      </div>
      
      <div className="chart-note">
        Trade Balance = Exports − Imports (goods & services, current US$)
      </div>
    </div>
  );
}
