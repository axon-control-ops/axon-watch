import { describe, expect, it } from 'vitest';
import { researchFaviconUrl, researchHostname } from './research-favicon';

describe('researchFavicon', () => {
  it('extracts hostname without www', () => {
    expect(researchHostname('https://www.example.com/docs')).toBe('example.com');
  });

  it('builds favicon url for valid hosts', () => {
    expect(researchFaviconUrl('https://vitejs.dev/guide/')).toContain('domain=vitejs.dev');
  });

  it('returns null for blank urls', () => {
    expect(researchFaviconUrl('about:blank')).toBeNull();
    expect(researchFaviconUrl('')).toBeNull();
  });
});
