import type { SourceResult } from '../types';

interface SourceResultsProps {
  results: SourceResult[];
}

export function SourceResults({ results }: SourceResultsProps) {
  if (results.length === 0) return null;

  return (
    <div className="source-results">
      <h3>Data Sources</h3>
      <div className="source-badges">
        {results.map((result) => (
          <div 
            key={result.name} 
            className={`source-badge ${result.success ? 'success' : 'error'}`}
          >
            <span className="source-icon">
              {result.success ? '✓' : '✗'}
            </span>
            <span className="source-name">{result.name}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
