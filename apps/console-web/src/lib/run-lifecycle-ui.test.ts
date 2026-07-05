import { describe, expect, it } from 'vitest';

import { isOperatorCompletablePhase } from './run-lifecycle-ui';

describe('run-lifecycle-ui', () => {
  it('allows complete on review_ready, executing, and paused', () => {
    expect(isOperatorCompletablePhase('review_ready')).toBe(true);
    expect(isOperatorCompletablePhase('executing')).toBe(true);
    expect(isOperatorCompletablePhase('paused')).toBe(true);
  });

  it('blocks complete on terminal phases', () => {
    expect(isOperatorCompletablePhase('completed')).toBe(false);
    expect(isOperatorCompletablePhase('cancelled')).toBe(false);
  });
});
