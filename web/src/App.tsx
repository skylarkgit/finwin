import { useState } from 'react';
import { fetchContext } from './api';
import { SearchBar } from './components/SearchBar';
import { FinancialsCard } from './components/FinancialsCard';
import { NewsCard } from './components/NewsCard';
import { SourceResults } from './components/SourceResults';
import { MacroDashboard } from './components/macro/MacroDashboard';
import type { StockContext } from './types';
import './App.css';

type View = 'stock' | 'macro';

function App() {
  const [view, setView] = useState<View>('macro');
  const [context, setContext] = useState<StockContext | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSearch = async (symbol: string, query: string) => {
    setIsLoading(true);
    setError(null);
    
    try {
      const result = await fetchContext(
        symbol || undefined,
        query || undefined
      );
      setContext(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch context');
      setContext(null);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-content">
          <h1>🏦 Finwin</h1>
          <nav className="app-nav">
            <button 
              className={`nav-btn ${view === 'macro' ? 'active' : ''}`}
              onClick={() => setView('macro')}
            >
              🌍 Global Wealth
            </button>
            <button 
              className={`nav-btn ${view === 'stock' ? 'active' : ''}`}
              onClick={() => setView('stock')}
            >
              📈 Stock Context
            </button>
          </nav>
        </div>
        <p className="subtitle">
          {view === 'macro' 
            ? 'Understanding the Movement of Global Wealth'
            : 'Financial Context Aggregator'
          }
        </p>
      </header>

      <main className="app-main">
        {view === 'macro' ? (
          <MacroDashboard />
        ) : (
          <>
            <SearchBar onSearch={handleSearch} isLoading={isLoading} />

            {error && (
              <div className="error-banner">
                <span className="error-icon">⚠️</span>
                {error}
              </div>
            )}

            {isLoading && (
              <div className="loading">
                <div className="spinner"></div>
                <p>Gathering context...</p>
              </div>
            )}

            {context && !isLoading && (
              <div className="context-results">
                <div className="context-header">
                  <h2>{context.meta.label}</h2>
                  <span className="timestamp">
                    Generated: {new Date(context.meta.generated_at_utc).toLocaleString()}
                  </span>
                </div>

                <SourceResults results={context.source_results} />

                <div className="results-grid">
                  {context.financials && (
                    <section className="financials-section">
                      <FinancialsCard financials={context.financials} />
                    </section>
                  )}

                  {context.news.length > 0 && (
                    <section className="news-section">
                      <h3>📰 News ({context.news.length})</h3>
                      <div className="news-grid">
                        {context.news.map((article, index) => (
                          <NewsCard key={`${article.link}-${index}`} article={article} />
                        ))}
                      </div>
                    </section>
                  )}
                </div>

                {context.all_texts.length > 0 && (
                  <section className="raw-text-section">
                    <details>
                      <summary>
                        📄 Raw Text Data ({context.all_texts.length} items)
                      </summary>
                      <div className="raw-texts">
                        {context.all_texts.map((text, index) => (
                          <pre key={index} className="raw-text">
                            {text.slice(0, 500)}
                            {text.length > 500 ? '...' : ''}
                          </pre>
                        ))}
                      </div>
                    </details>
                  </section>
                )}
              </div>
            )}
          </>
        )}
      </main>

      <footer className="app-footer">
        <p>Powered by Finwin Library • Data from World Bank, yfinance</p>
      </footer>
    </div>
  );
}

export default App;
