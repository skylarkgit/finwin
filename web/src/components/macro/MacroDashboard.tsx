import { useState, useEffect, useMemo } from 'react';
import { fetchMacroDashboard, formatGDP, formatGrowth } from '../../api';
import type { MacroDashboardData, CountryInfo, MacroDataPoint } from '../../types';
import './MacroDashboard.css';

type SortField = 'rank' | 'name' | 'region' | 'gdp' | 'growth';
type SortDirection = 'asc' | 'desc';

export function MacroDashboard() {
  const [data, setData] = useState<MacroDashboardData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedCountries, setSelectedCountries] = useState<string[]>([]);
  
  // Pagination & sorting state
  const [currentPage, setCurrentPage] = useState(1);
  const [sortField, setSortField] = useState<SortField>('gdp');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');
  const itemsPerPage = 20;

  useEffect(() => {
    loadDashboard();
  }, []);

  const loadDashboard = async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      // Request more countries for pagination
      const result = await fetchMacroDashboard(undefined, undefined, 100);
      setData(result);
      // Select top 5 by default for comparison
      setSelectedCountries(result.countries.slice(0, 5).map(c => c.code));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load dashboard');
    } finally {
      setIsLoading(false);
    }
  };

  // Sorted and paginated countries
  const { sortedCountries, totalPages, paginatedCountries } = useMemo(() => {
    if (!data) return { sortedCountries: [], totalPages: 0, paginatedCountries: [] };
    
    const sorted = [...data.countries].sort((a, b) => {
      let comparison = 0;
      switch (sortField) {
        case 'rank':
          comparison = (a.latest_gdp ?? 0) - (b.latest_gdp ?? 0);
          break;
        case 'name':
          comparison = a.name.localeCompare(b.name);
          break;
        case 'region':
          comparison = (a.region || '').localeCompare(b.region || '');
          break;
        case 'gdp':
          comparison = (a.latest_gdp ?? 0) - (b.latest_gdp ?? 0);
          break;
        case 'growth':
          comparison = (a.gdp_growth ?? 0) - (b.gdp_growth ?? 0);
          break;
      }
      return sortDirection === 'desc' ? -comparison : comparison;
    });
    
    const total = Math.ceil(sorted.length / itemsPerPage);
    const start = (currentPage - 1) * itemsPerPage;
    const paginated = sorted.slice(start, start + itemsPerPage);
    
    return { sortedCountries: sorted, totalPages: total, paginatedCountries: paginated };
  }, [data, sortField, sortDirection, currentPage]);

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(d => d === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection(field === 'name' || field === 'region' ? 'asc' : 'desc');
    }
    setCurrentPage(1);
  };

  if (isLoading) {
    return (
      <div className="macro-dashboard loading">
        <div className="spinner"></div>
        <p>Loading global economic data...</p>
        <p className="loading-note">First load may take 30-60 seconds while fetching from World Bank API</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="macro-dashboard error">
        <h2>⚠️ Error Loading Dashboard</h2>
        <p>{error}</p>
        <button onClick={loadDashboard}>Retry</button>
      </div>
    );
  }

  if (!data) return null;

  const { gdp_summary, gdp_by_country } = data;

  return (
    <div className="macro-dashboard">
      <header className="dashboard-header">
        <h1>🌍 Global Wealth Dashboard</h1>
        <p className="subtitle">Understanding the Movement of Global Wealth</p>
        <div className="data-info">
          <span>Source: {gdp_summary.data_source}</span>
          <span>•</span>
          <span>{gdp_summary.countries_count} countries</span>
          <span>•</span>
          <span>Updated: {gdp_summary.last_updated ? new Date(gdp_summary.last_updated).toLocaleDateString() : 'N/A'}</span>
        </div>
      </header>

      {/* World GDP Summary Cards */}
      <section className="summary-cards">
        <div className="card world-gdp">
          <h3>World GDP</h3>
          <div className="value">{formatGDP(gdp_summary.world_gdp_total)}</div>
          <div className="year">{gdp_summary.world_gdp_year}</div>
        </div>
        <div className={`card world-growth ${(gdp_summary.world_gdp_growth ?? 0) >= 0 ? 'positive' : 'negative'}`}>
          <h3>World GDP Growth</h3>
          <div className="value">{formatGrowth(gdp_summary.world_gdp_growth)}</div>
          <div className="year">Year-over-Year</div>
        </div>
        <div className="card countries-count">
          <h3>Economies Tracked</h3>
          <div className="value">{gdp_summary.countries_count}</div>
          <div className="year">Countries</div>
        </div>
      </section>

      {/* World GDP History Chart */}
      <section className="section world-gdp-history">
        <h2>📈 World GDP Over Time (20 Years)</h2>
        <WorldGDPChart data={gdp_summary.world_gdp_history} />
      </section>

      {/* Regional Breakdown */}
      <section className="section regional-breakdown">
        <h2>🗺️ GDP by Region</h2>
        <RegionalBreakdown regions={gdp_summary.region_totals} />
      </section>

      {/* Top Economies Table */}
      <section className="section top-economies">
        <h2>🏆 Top Economies</h2>
        <TopEconomiesTable 
          countries={paginatedCountries}
          allCountries={sortedCountries}
          selectedCountries={selectedCountries}
          onToggleCountry={(code) => {
            setSelectedCountries(prev => 
              prev.includes(code) 
                ? prev.filter(c => c !== code)
                : [...prev, code]
            );
          }}
          sortField={sortField}
          sortDirection={sortDirection}
          onSort={handleSort}
          currentPage={currentPage}
          totalPages={totalPages}
          onPageChange={setCurrentPage}
          startRank={(currentPage - 1) * itemsPerPage + 1}
        />
      </section>

      {/* Country Comparison Chart */}
      {selectedCountries.length > 0 && (
        <section className="section country-comparison">
          <h2>📊 Country Comparison ({selectedCountries.length} selected)</h2>
          <CountryComparisonChart 
            countries={selectedCountries}
            gdpData={gdp_by_country}
            allCountries={sortedCountries}
          />
        </section>
      )}
    </div>
  );
}

// =============================================================================
// Sub-components
// =============================================================================

function WorldGDPChart({ data }: { data: MacroDataPoint[] }) {
  const sortedData = [...data]
    .filter(d => d.value !== null)
    .sort((a, b) => a.year - b.year);
  
  if (sortedData.length === 0) return <p>No data available</p>;

  const values = sortedData.map(d => d.value ?? 0);
  const maxValue = Math.max(...values);
  const minValue = Math.min(...values);
  const minYear = sortedData[0].year;
  const maxYear = sortedData[sortedData.length - 1].year;

  // Y-axis scale values
  const yAxisValues = [0, 0.25, 0.5, 0.75, 1].map(ratio => maxValue * ratio);

  return (
    <div className="chart world-gdp-chart">
      <div className="chart-y-axis">
        {yAxisValues.reverse().map((val, i) => (
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

function RegionalBreakdown({ regions }: { regions: Record<string, number> }) {
  const sortedRegions = Object.entries(regions)
    .filter(([name]) => name && name !== '')
    .sort((a, b) => b[1] - a[1]);
  
  const total = sortedRegions.reduce((sum, [, val]) => sum + val, 0);

  const colors = [
    '#3498db', '#2ecc71', '#e74c3c', '#f39c12', 
    '#9b59b6', '#1abc9c', '#e67e22', '#34495e'
  ];

  return (
    <div className="regional-breakdown-content">
      <div className="region-bars">
        {sortedRegions.map(([name, value], idx) => (
          <div key={name} className="region-bar">
            <div className="region-info">
              <span 
                className="region-color" 
                style={{ backgroundColor: colors[idx % colors.length] }}
              />
              <span className="region-name">{name}</span>
            </div>
            <div className="region-bar-container">
              <div 
                className="region-bar-fill"
                style={{ 
                  width: `${(value / sortedRegions[0][1]) * 100}%`,
                  backgroundColor: colors[idx % colors.length]
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

function TopEconomiesTable({ 
  countries, 
  allCountries,
  selectedCountries,
  onToggleCountry,
  sortField,
  sortDirection,
  onSort,
  currentPage,
  totalPages,
  onPageChange,
  startRank,
}: { 
  countries: CountryInfo[];
  allCountries: CountryInfo[];
  selectedCountries: string[];
  onToggleCountry: (code: string) => void;
  sortField: SortField;
  sortDirection: SortDirection;
  onSort: (field: SortField) => void;
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  startRank: number;
}) {
  const SortHeader = ({ field, children }: { field: SortField; children: React.ReactNode }) => (
    <th 
      onClick={() => onSort(field)}
      className={`sortable ${sortField === field ? 'active' : ''}`}
    >
      {children}
      {sortField === field && (
        <span className="sort-indicator">{sortDirection === 'asc' ? ' ▲' : ' ▼'}</span>
      )}
    </th>
  );

  return (
    <div className="economies-table-container">
      <table className="economies-table">
        <thead>
          <tr>
            <th>Compare</th>
            <SortHeader field="rank">Rank</SortHeader>
            <SortHeader field="name">Country</SortHeader>
            <SortHeader field="region">Region</SortHeader>
            <SortHeader field="gdp">GDP</SortHeader>
            <SortHeader field="growth">Growth</SortHeader>
            <th>Year</th>
          </tr>
        </thead>
        <tbody>
          {countries.map((country, index) => (
            <tr 
              key={country.code}
              className={selectedCountries.includes(country.code) ? 'selected' : ''}
            >
              <td>
                <input 
                  type="checkbox"
                  checked={selectedCountries.includes(country.code)}
                  onChange={() => onToggleCountry(country.code)}
                />
              </td>
              <td className="rank">{startRank + index}</td>
              <td className="country">
                <span className="country-code">{country.code}</span>
                <span className="country-name">{country.name}</span>
              </td>
              <td className="region">{country.region || '-'}</td>
              <td className="gdp">{formatGDP(country.latest_gdp)}</td>
              <td className={`growth ${(country.gdp_growth ?? 0) >= 0 ? 'positive' : 'negative'}`}>
                {formatGrowth(country.gdp_growth)}
              </td>
              <td className="year">{country.latest_gdp_year}</td>
            </tr>
          ))}
        </tbody>
      </table>
      
      {/* Pagination */}
      {totalPages > 1 && (
        <div className="pagination">
          <button 
            onClick={() => onPageChange(1)} 
            disabled={currentPage === 1}
          >
            ««
          </button>
          <button 
            onClick={() => onPageChange(currentPage - 1)} 
            disabled={currentPage === 1}
          >
            «
          </button>
          <span className="page-info">
            Page {currentPage} of {totalPages} ({allCountries.length} countries)
          </span>
          <button 
            onClick={() => onPageChange(currentPage + 1)} 
            disabled={currentPage === totalPages}
          >
            »
          </button>
          <button 
            onClick={() => onPageChange(totalPages)} 
            disabled={currentPage === totalPages}
          >
            »»
          </button>
        </div>
      )}
    </div>
  );
}

function CountryComparisonChart({ 
  countries, 
  gdpData,
  allCountries,
}: { 
  countries: string[];
  gdpData: Record<string, import('../../types').MacroTimeSeries>;
  allCountries: CountryInfo[];
}) {
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

  const colors = [
    '#3498db', '#2ecc71', '#e74c3c', '#f39c12', 
    '#9b59b6', '#1abc9c', '#e67e22', '#34495e',
    '#c0392b', '#27ae60'
  ];

  // Get country names from allCountries or gdpData
  const getCountryName = (code: string) => {
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
            <span 
              className="legend-color" 
              style={{ backgroundColor: colors[idx % colors.length] }}
            />
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
              x1="70" 
              y1={270 - ratio * 240} 
              x2="780" 
              y2={270 - ratio * 240}
              stroke="#333"
              strokeDasharray="2,2"
            />
          ))}
          
          {/* Lines for each country */}
          {countries.map((code, idx) => {
            const data = gdpData[code];
            if (!data) return null;
            
            const points = years.map((year, i) => {
              const point = data.data.find(d => d.year === year);
              const x = 70 + (i / Math.max(years.length - 1, 1)) * 700;
              const y = point?.value 
                ? 270 - (point.value / maxValue) * 240 
                : null;
              return { x, y, year, value: point?.value };
            }).filter(p => p.y !== null);
            
            if (points.length === 0) return null;
            
            const pathD = points
              .map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`)
              .join(' ');
            
            return (
              <g key={code}>
                <path 
                  d={pathD}
                  fill="none"
                  stroke={colors[idx % colors.length]}
                  strokeWidth="2"
                />
                {points.map((p, i) => (
                  <circle
                    key={i}
                    cx={p.x}
                    cy={p.y!}
                    r="4"
                    fill={colors[idx % colors.length]}
                  >
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
              y="290"
              textAnchor="middle"
              fill="#999"
              fontSize="11"
            >
              {year}
            </text>
          ))}
          
          {/* Y-axis labels */}
          {[0, 0.25, 0.5, 0.75, 1].map(ratio => (
            <text 
              key={ratio}
              x="65"
              y={275 - ratio * 240}
              textAnchor="end"
              fill="#999"
              fontSize="10"
            >
              {formatGDP(maxValue * ratio)}
            </text>
          ))}
        </svg>
      </div>
    </div>
  );
}
