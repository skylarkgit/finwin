import type { CountryInfo } from '../../types';
import { formatGDP, formatGrowth, formatPopulation, formatGDPPerCapita, formatFDI, formatTradeBalance, formatTradeBalancePct } from '../../api';

type SortField = 'rank' | 'name' | 'region' | 'gdp' | 'growth' | 'population' | 'gdp_per_capita' | 'fdi_net' | 'trade_balance' | 'trade_pct';
type SortDirection = 'asc' | 'desc';

export interface TopEconomiesTableProps {
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
}

function SortHeader({ 
  field, 
  sortField, 
  sortDirection, 
  onSort, 
  children 
}: { 
  field: SortField; 
  sortField: SortField;
  sortDirection: SortDirection;
  onSort: (field: SortField) => void;
  children: React.ReactNode;
}) {
  return (
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
}

export function TopEconomiesTable({ 
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
}: TopEconomiesTableProps) {
  return (
    <div className="economies-table-container">
      <table className="economies-table">
        <thead>
          <tr>
            <th>Compare</th>
            <SortHeader field="rank" sortField={sortField} sortDirection={sortDirection} onSort={onSort}>Rank</SortHeader>
            <SortHeader field="name" sortField={sortField} sortDirection={sortDirection} onSort={onSort}>Country</SortHeader>
            <SortHeader field="region" sortField={sortField} sortDirection={sortDirection} onSort={onSort}>Region</SortHeader>
            <SortHeader field="gdp" sortField={sortField} sortDirection={sortDirection} onSort={onSort}>GDP</SortHeader>
            <SortHeader field="growth" sortField={sortField} sortDirection={sortDirection} onSort={onSort}>Growth</SortHeader>
            <SortHeader field="gdp_per_capita" sortField={sortField} sortDirection={sortDirection} onSort={onSort}>GDP/Capita</SortHeader>
            <SortHeader field="population" sortField={sortField} sortDirection={sortDirection} onSort={onSort}>Population</SortHeader>
            <SortHeader field="fdi_net" sortField={sortField} sortDirection={sortDirection} onSort={onSort}>FDI Net</SortHeader>
            <SortHeader field="trade_balance" sortField={sortField} sortDirection={sortDirection} onSort={onSort}>Trade Bal.</SortHeader>
            <SortHeader field="trade_pct" sortField={sortField} sortDirection={sortDirection} onSort={onSort}>Trade/GDP</SortHeader>
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
              <td className="gdp-per-capita">{formatGDPPerCapita(country.gdp_per_capita)}</td>
              <td className="population">{formatPopulation(country.population)}</td>
              <td className={`fdi-net ${(country.fdi_net ?? 0) >= 0 ? 'positive' : 'negative'}`}>
                {formatFDI(country.fdi_net)}
              </td>
              <td className={`trade-balance ${(country.trade_balance ?? 0) >= 0 ? 'surplus' : 'deficit'}`}>
                {formatTradeBalance(country.trade_balance)}
              </td>
              <td className={`trade-pct ${(country.trade_balance_pct ?? 0) >= 0 ? 'surplus' : 'deficit'}`}>
                {formatTradeBalancePct(country.trade_balance_pct)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      
      {totalPages > 1 && (
        <div className="pagination">
          <button onClick={() => onPageChange(1)} disabled={currentPage === 1}>««</button>
          <button onClick={() => onPageChange(currentPage - 1)} disabled={currentPage === 1}>«</button>
          <span className="page-info">
            Page {currentPage} of {totalPages} ({allCountries.length} countries)
          </span>
          <button onClick={() => onPageChange(currentPage + 1)} disabled={currentPage === totalPages}>»</button>
          <button onClick={() => onPageChange(totalPages)} disabled={currentPage === totalPages}>»»</button>
        </div>
      )}
    </div>
  );
}

export type { SortField, SortDirection };
