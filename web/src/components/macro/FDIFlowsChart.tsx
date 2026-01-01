import type { CountryInfo } from '../../types';
import { formatFDI } from '../../api';

interface FDIFlowsChartProps {
  countries: CountryInfo[];
  limit?: number;
}

export function FDIFlowsChart({ countries, limit = 15 }: FDIFlowsChartProps) {
  // Get countries with FDI data, sorted by inflows
  const countriesWithFDI = countries
    .filter(c => c.fdi_inflows !== null && c.region) // Only actual countries
    .sort((a, b) => (b.fdi_inflows ?? 0) - (a.fdi_inflows ?? 0))
    .slice(0, limit);

  if (countriesWithFDI.length === 0) {
    return <div className="no-data">No FDI data available</div>;
  }

  const maxInflow = Math.max(...countriesWithFDI.map(c => c.fdi_inflows ?? 0));
  const maxOutflow = Math.max(...countriesWithFDI.map(c => Math.abs(c.fdi_outflows ?? 0)));
  const maxValue = Math.max(maxInflow, maxOutflow);

  return (
    <div className="fdi-flows-chart">
      <div className="chart-legend">
        <span className="legend-item inflow">
          <span className="color-box"></span> FDI Inflows
        </span>
        <span className="legend-item outflow">
          <span className="color-box"></span> FDI Outflows
        </span>
      </div>
      
      <div className="fdi-bars">
        {countriesWithFDI.map((country) => {
          const inflowWidth = maxValue > 0 
            ? ((country.fdi_inflows ?? 0) / maxValue) * 100 
            : 0;
          const outflowWidth = maxValue > 0 
            ? (Math.abs(country.fdi_outflows ?? 0) / maxValue) * 100 
            : 0;
          
          const netFDI = country.fdi_net ?? 0;
          
          return (
            <div key={country.code} className="fdi-bar-row">
              <div className="country-label">
                <span className="code">{country.code}</span>
                <span className="name">{country.name}</span>
              </div>
              
              <div className="bar-container">
                <div className="dual-bar">
                  <div 
                    className="bar inflow" 
                    style={{ width: `${inflowWidth}%` }}
                    title={`Inflows: ${formatFDI(country.fdi_inflows)}`}
                  />
                  <div 
                    className="bar outflow" 
                    style={{ width: `${outflowWidth}%` }}
                    title={`Outflows: ${formatFDI(country.fdi_outflows)}`}
                  />
                </div>
              </div>
              
              <div className="values">
                <span className="inflow-value">{formatFDI(country.fdi_inflows)}</span>
                <span className={`net-value ${netFDI >= 0 ? 'positive' : 'negative'}`}>
                  Net: {formatFDI(netFDI)}
                </span>
              </div>
            </div>
          );
        })}
      </div>
      
      <div className="chart-note">
        FDI = Foreign Direct Investment (net flows, current US$)
      </div>
    </div>
  );
}
