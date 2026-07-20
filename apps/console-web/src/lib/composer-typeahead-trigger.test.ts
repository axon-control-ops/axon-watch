import { describe, expect, it } from 'vitest';

import {
  detectComposerCaretToken,
  replaceComposerToken,
} from './composer-typeahead-trigger';

describe('composer-typeahead-trigger', () => {
  it('detects slash token at draft start', () => {
    const token = detectComposerCaretToken('/coder', 6);
    expect(token).toEqual({
      kind: 'slash',
      token: '/coder',
      query: 'coder',
      start: 0,
      end: 6,
    });
  });

  it('ignores slash after other text', () => {
    expect(detectComposerCaretToken('hello /coder', 12)).toBeNull();
  });

  it('detects mention token at word boundary', () => {
    const token = detectComposerCaretToken('see @apps/console', 17);
    expect(token).toMatchObject({
      kind: 'mention',
      token: '@apps/console',
      query: 'apps/console',
      start: 4,
      end: 17,
    });
  });

  it('replaces a token and returns the next caret', () => {
    const result = replaceComposerToken('see @ap', { start: 4, end: 7 }, '@file:apps/x.ts ');
    expect(result.next).toBe('see @file:apps/x.ts ');
    expect(result.caret).toBe(result.next.length);
  });
});
