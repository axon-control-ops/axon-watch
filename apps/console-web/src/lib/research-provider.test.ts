import { describe, expect, it } from 'vitest';
import {
  formatResearchKindLabel,
  formatResearchProviderLabel,
  inferResearchBlockKind,
} from './research-provider';

describe('research-provider', () => {
  it('formats known provider labels', () => {
    expect(formatResearchProviderLabel('duckduckgo_instant')).toBe('DuckDuckGo');
  });

  it('formats unknown providers from snake case', () => {
    expect(formatResearchProviderLabel('custom_search')).toBe('Custom Search');
  });

  it('infers block kind from query labels', () => {
    expect(inferResearchBlockKind('Page fetch')).toBe('fetch');
    expect(inferResearchBlockKind('Web search')).toBe('search');
  });

  it('formats kind labels', () => {
    expect(formatResearchKindLabel('fetch')).toBe('Page fetch');
    expect(formatResearchKindLabel('search')).toBe('Web search');
  });
});
