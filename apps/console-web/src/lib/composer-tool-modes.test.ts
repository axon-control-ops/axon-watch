import { describe, expect, it } from 'vitest';

import { isToolCapableComposerMode } from './composer-tool-modes';

describe('composer-tool-modes', () => {
  it('treats agent and debug as tool-capable', () => {
    expect(isToolCapableComposerMode('agent')).toBe(true);
    expect(isToolCapableComposerMode('debug')).toBe(true);
    expect(isToolCapableComposerMode('DEBUG')).toBe(true);
  });

  it('rejects ask, plan, kairo, and empty values', () => {
    expect(isToolCapableComposerMode('ask')).toBe(false);
    expect(isToolCapableComposerMode('plan')).toBe(false);
    expect(isToolCapableComposerMode('kairo')).toBe(false);
    expect(isToolCapableComposerMode('')).toBe(false);
    expect(isToolCapableComposerMode(null)).toBe(false);
    expect(isToolCapableComposerMode(undefined)).toBe(false);
  });
});
