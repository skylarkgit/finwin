import { useState, useEffect, useMemo } from 'react';
import { fetchMacroDashboard, formatGDP, formatGrowth } from '../../api';
import type { MacroDashboardData } from '../../types';
import { WorldGDPChart } from './WorldGDPChart';
import { RegionalBreakdown } from './RegionalBreakdown';
import { TopEconomiesTable, type SortField, type SortDirection } from './TopEconomiesTable';
import { CountryComparisonChart } from './CountryComparisonChart';
import './MacroDashboard.css';

const ITEMS_PER_PAGE = 20;

export function MacroDashboard() {
  const [data, setData] = useState<MacroDashboardData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedCountries, setSelectedCountries] = useState<string[]>([]);
  
  // Pagination & sorting state
  const [currentPage, setCurrentPage] = useState(1);
  const [sortField, setSortField] = useState<SortField>('gdp');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');

  useEffect(() => {
    loadDashboard();
  }, []);

  const loadDashboard = async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      const result = await fetchMacroDashboard(undefined, undefined, 100);
      setData(result);
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
        case 'gdp':
          comparison = (a.latest_gdp ?? 0) - (b.latest_gdp ?? 0);
          break;
        case 'name':
          comparison = a.name.localeCompare(b.name);
          break;
        case 'region':
          comparison = (a.region || '').localeCompare(b.region || '');
          break;
        case 'growth':
          comparison = (a.gdp_growth ?? 0) - (b.gdp_growth ?? 0);
          break;
        case 'population':
          comparison = (a.population ?? 0) - (b.population ?? 0);
          break;
        case 'gdp_per_capita':
          comparison = (a.gdp_per_capita ?? 0) - (b.gdp_per_capita ?? 0);
          break;
      }
      return sortDirection === 'desc' ? -comparison : comparison;
    });
    
    const total = Math.ceil(sorted.length / ITEMS_PER_PAGE);
    const start = (currentPage - 1) * ITEMS_PER_PAGE;
    const paginated = sorted.slice(start, start + ITEMS_PER_PAGE);
    
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

  const handleToggleCountry = (code: string) => {
    setSelectedCountries(prev => 
      prev.includes(code) ? prev.filter(c => c !== code) : [...prev, code]
    );
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

      {/* Summary Cards */}
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

      {/* Charts & Tables */}
      <section className="section world-gdp-history">
        <h2>📈 World GDP Over Time (20 Years)</h2>
        <WorldGDPChart data={gdp_summary.world_gdp_history} />
      </section>

      <section className="section regional-breakdown">
        <h2>🗺️ GDP by Region</h2>
        <RegionalBreakdown regions={gdp_summary.region_totals} />
      </section>

      <section className="section top-economies">
        <h2>🏆 Top Economies</h2>
        <TopEconomiesTable 
          countries={paginatedCountries}
          allCountries={sortedCountries}
          selectedCountries={selectedCountries}
          onToggleCountry={handleToggleCountry}
          sortField={sortField}
          sortDirection={sortDirection}
          onSort={handleSort}
          currentPage={currentPage}
          totalPages={totalPages}
          onPageChange={setCurrentPage}
          startRank={(currentPage - 1) * ITEMS_PER_PAGE + 1}
        />
      </section>

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
