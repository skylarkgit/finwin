import { formatGDP } from '../../api';
import { getColor } from './chartUtils';

interface RegionalBreakdownProps {
  regions: Record<string, number>;
}

export function RegionalBreakdown({ regions }: RegionalBreakdownProps) {
  const sortedRegions = Object.entries(regions)
    .filter(([name]) => name && name !== '')
    .sort((a, b) => b[1] - a[1]);
  
  const total = sortedRegions.reduce((sum, [, val]) => sum + val, 0);

  return (
    <div className="regional-breakdown-content">
      <div className="region-bars">
        {sortedRegions.map(([name, value], idx) => (
          <div key={name} className="region-bar">
            <div className="region-info">
              <span 
                className="region-color" 
                style={{ backgroundColor: getColor(idx) }}
              />
              <span className="region-name">{name}</span>
            </div>
            <div className="region-bar-container">
              <div 
                className="region-bar-fill"
                style={{ 
                  width: `${(value / sortedRegions[0][1]) * 100}%`,
                  backgroundColor: getColor(idx)
                }}
              />
            </div>
            <div className="region-value">
              <span>{formatGDP(value)}</span>
              <span className="region-percent">
                ({((value / total) * 100).toFixed(1)}%)
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
