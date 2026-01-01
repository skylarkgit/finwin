import type { NewsArticle } from '../types';

interface NewsCardProps {
  article: NewsArticle;
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return '';
  try {
    const date = new Date(dateStr);
    return date.toLocaleDateString(undefined, {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  } catch {
    return dateStr;
  }
}

export function NewsCard({ article }: NewsCardProps) {
  const url = article.resolved_link || article.link;
  
  return (
    <a 
      href={url} 
      target="_blank" 
      rel="noopener noreferrer" 
      className="card news-card"
    >
      <h4 className="news-title">{article.title}</h4>
      <div className="news-meta">
        {article.source && (
          <span className="news-source">{article.source}</span>
        )}
        {article.published && (
          <span className="news-date">{formatDate(article.published)}</span>
        )}
      </div>
      {article.extracted_text && (
        <p className="news-excerpt">
          {article.extracted_text.slice(0, 200)}
          {article.extracted_text.length > 200 ? '...' : ''}
        </p>
      )}
    </a>
  );
}
