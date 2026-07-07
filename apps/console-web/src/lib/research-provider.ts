export type ResearchBlockKind = 'search' | 'fetch';

export function inferResearchBlockKind(query: string): ResearchBlockKind | undefined {
  const normalized = query.trim().toLowerCase();
  if (normalized === 'page fetch' || normalized.startsWith('fetch ')) {
    return 'fetch';
  }
  if (normalized === 'web search' || normalized.startsWith('search ')) {
    return 'search';
  }
  return undefined;
}

export function formatResearchProviderLabel(provider: string): string {
  const normalized = provider.trim().toLowerCase().replace(/-/g, '_');
  if (!normalized) {
    return '';
  }

  const labels: Record<string, string> = {
    duckduckgo_instant: 'DuckDuckGo',
    duckduckgo: 'DuckDuckGo',
    brave: 'Brave',
    bing: 'Bing',
    google: 'Google',
    serpapi: 'SerpAPI',
    tavily: 'Tavily',
  };

  if (labels[normalized]) {
    return labels[normalized];
  }

  return normalized
    .split('_')
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}

export function formatResearchKindLabel(kind: ResearchBlockKind | undefined): string {
  if (kind === 'fetch') {
    return 'Page fetch';
  }
  if (kind === 'search') {
    return 'Web search';
  }
  return '';
}
