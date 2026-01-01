import { useState, type FormEvent } from 'react';

interface SearchBarProps {
  onSearch: (symbol: string, query: string) => void;
  isLoading: boolean;
}

export function SearchBar({ onSearch, isLoading }: SearchBarProps) {
  const [symbol, setSymbol] = useState('');
  const [query, setQuery] = useState('');

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (symbol.trim() || query.trim()) {
      onSearch(symbol.trim(), query.trim());
    }
  };

  return (
    <form className="search-bar" onSubmit={handleSubmit}>
      <div className="search-inputs">
        <div className="input-group">
          <label htmlFor="symbol">Stock Symbol</label>
          <input
            id="symbol"
            type="text"
            placeholder="e.g., TCS.NS, AAPL"
            value={symbol}
            onChange={(e) => setSymbol(e.target.value)}
          />
        </div>
        <div className="input-group">
          <label htmlFor="query">Search Query</label>
          <input
            id="query"
            type="text"
            placeholder="e.g., Tata Consultancy Services"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>
      </div>
      <button type="submit" disabled={isLoading || (!symbol.trim() && !query.trim())}>
        {isLoading ? 'Loading...' : 'Gather Context'}
      </button>
    </form>
  );
}
