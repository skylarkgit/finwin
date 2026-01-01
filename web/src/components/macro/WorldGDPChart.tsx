import type { MacroDataPoint } from '../../types';
import { formatGDP } from '../../api';

interface WorldGDPChartProps {
  data: MacroDataPoint[];
}

export function WorldGDPChart({ data }: WorldGDPChartProps) {
  const sortedData = [...data]
    .filter(d => d.value !== null)
    .sort((a, b) => a.year - b.year);
  
  if (sortedData.length === 0) return <p>No data available</p>;

  const values = sortedData.map(d => d.value ?? 0);
  const maxValue = Math.max(...values);

  // Y-axis scale values (reverse for top-to-bottom display)
  const yAxisValues = [1, 0.75, 0.5, 0.25, 0].map(ratio => maxValue * ratio);

  return (
    <div className="chart world-gdp-chart">
      <div className="chart-y-axis">
        {yAxisValues.map((val, i) => (
          <span key={i} className="y-label">{formatGDP(val)}</span>
        ))}
      </div>
      <div className="chart-content">
        <div className="chart-bars">
          {sortedData.map((point) => (
            <div 
              key={point.year} 
              className="bar-container"
              title={`${point.year}: ${formatGDP(point.value)}`}
            >
              <div 
                className="bar"
                style={{ height: `${((point.value ?? 0) / maxValue) * 100}%` }}
              />
              <span className="bar-label">{point.year}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
