import { describe, expect, it } from 'vitest';

import { readAppSurface } from './app-surface-route';

describe('app surface route', () => {
  it('maps foundation paths to isolated surfaces', () => {
    expect(readAppSurface('/vault')).toBe('vault');
    expect(readAppSurface('/data')).toBe('data');
    expect(readAppSurface('/mobile')).toBe('mobile');
    expect(readAppSurface('/settings')).toBe('settings');
    expect(readAppSurface('/')).toBe('console');
  });
});
