import { describe, expect, it, vi } from 'vitest';

vi.mock('react-native', () => ({
  Platform: { OS: 'web' },
}));

import { explainFetchFailure, surfaceErrorHint } from '../apps/console-mobile/fetch-hints';

describe('console mobile fetch hints', () => {
  it('turns opaque browser fetch failures into explicit CORS guidance', () => {
    expect(explainFetchFailure('Failed to fetch', 'http://127.0.0.1:8787')).toContain(
      'allows that origin with CORS',
    );
  });

  it('keeps the follow-up hint specific for localhost browser development', () => {
    const error = explainFetchFailure('Failed to fetch', 'http://localhost:8787');
    expect(surfaceErrorHint('http://localhost:8787', error)).toContain(
      'http://localhost:8081',
    );
  });
});
