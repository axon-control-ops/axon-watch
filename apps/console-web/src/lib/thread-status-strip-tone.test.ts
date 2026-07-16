import { describe, expect, it } from 'vitest';

import {
  resolveThreadStatusStripTone,
  threadStatusStripClassNames,
} from './thread-status-strip-tone';

describe('thread-status-strip-tone', () => {
  it('maps composer mode and access to strip tones', () => {
    expect(resolveThreadStatusStripTone('ask', 'consultative')).toBe('ask');
    expect(resolveThreadStatusStripTone('plan', 'consultative')).toBe('plan');
    expect(resolveThreadStatusStripTone('agent', 'consultative')).toBe('agent');
    expect(resolveThreadStatusStripTone('agent', 'full')).toBe('agent-full');
    expect(resolveThreadStatusStripTone('debug', 'consultative')).toBe('debug');
    expect(resolveThreadStatusStripTone('debug', 'full')).toBe('debug-full');
  });

  it('adds streaming class only when streaming', () => {
    expect(
      threadStatusStripClassNames({ tone: 'plan', streaming: true }),
    ).toContain('conversation-seam__item--thread-status--streaming');
    expect(
      threadStatusStripClassNames({ tone: 'plan', streaming: false }),
    ).not.toContain('conversation-seam__item--thread-status--streaming');
  });
});
