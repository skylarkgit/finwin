import type { CountryInfo, MacroTimeSeries } from '../../types';
import { formatGDP } from '../../api';
import { getColor } from './chartUtils';

interface CountryComparisonChartProps {
  countries: string[];
  gdpData: Record<string, MacroTimeSeries>;
  allCountries: CountryInfo[];
}

export function CountryComparisonChart({ 
  countries, 
  gdpData,
  allCountries,
}: CountryComparisonChartProps) {
  // Get all years from selected countries
  const allYears = new Set<number>();
  countries.forEach(code => {
    const data = gdpData[code];
    if (data) {
      data.data.forEach(d => allYears.add(d.year));
    }
  });
  
  const years = Array.from(allYears).sort();
  
  // Find max value for scaling
  let maxValue = 0;
  countries.forEach(code => {
    const data = gdpData[code];
    if (data) {
      data.data.forEach(d => {
        if (d.value && d.value > maxValue) maxValue = d.value;
      });
    }
  });

  // Get country name by code
  const getCountryName = (code: string): string => {
    const info = allCountries.find(c => c.code === code);
    if (info) return info.name;
    const data = gdpData[code];
    return data?.country_name || code;
  };

  if (years.length === 0) {
    return <p className="no-data">No GDP data available for selected countries</p>;
  }

  return (
    <div className="comparison-chart">
      <div className="chart-legend-items">
        {countries.map((code, idx) => (
          <div key={code} className="legend-item">
            <span className="legend-color" style={{ backgroundColor: getColor(idx) }} />
            <span>{getCountryName(code)}</span>
          </div>
        ))}
      </div>
      
      <div className="multi-line-chart">
        <svg viewBox="0 0 800 300" preserveAspectRatio="xMidYMid meet">
          {/* Grid lines */}
          {[0, 0.25, 0.5, 0.75, 1].map(ratio => (
            <line 
              key={ratio}
              x1="70" y1={270 - ratio * 240} 
              x2="780" y2={270 - ratio * 240}
              stroke="#333" strokeDasharray="2,2"
            />
          ))}
          
          {/* Lines for each country */}
          {countries.map((code, idx) => {
            const data = gdpData[code];
            if (!data) return null;
            
            const points = years.map((year, i) => {
              const point = data.data.find(d => d.year === year);
              const x = 70 + (i / Math.max(years.length - 1, 1)) * 700;
              const y = point?.value ? 270 - (point.value / maxValue) * 240 : null;
              return { x, y, year, value: point?.value };
            }).filter(p => p.y !== null);
            
            if (points.length === 0) return null;
            
            const pathD = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ');
            
            return (
              <g key={code}>
                <path d={pathD} fill="none" stroke={getColor(idx)} strokeWidth="2" />
                {points.map((p, i) => (
                  <circle key={i} cx={p.x} cy={p.y!} r="4" fill={getColor(idx)}>
                    <title>{`${getCountryName(code)} (${p.year}): ${formatGDP(p.value ?? null)}`}</title>
                  </circle>
                ))}
              </g>
            );
          })}
          
          {/* X-axis labels */}
          {years.filter((_, i) => i % Math.max(1, Math.floor(years.length / 5)) === 0 || i === years.length - 1).map((year) => (
            <text 
              key={year}
              x={70 + (years.indexOf(year) / Math.max(years.length - 1, 1)) * 700}
              y="290" textAnchor="middle" fill="#999" fontSize="11"
            >
              {year}
            </text>
          ))}
          
          {/* Y-axis labels */}
          {[0, 0.25, 0.5, 0.75, 1].map(ratio => (
            <text key={ratio} x="65" y={275 - ratio * 240} textAnchor="end" fill="#999" fontSize="10">
              {formatGDP(maxValue * ratio)}
            </text>
          ))}
        </svg>
      </div>
    </div>
  );
}
