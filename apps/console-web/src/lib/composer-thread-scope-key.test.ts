import { describe, expect, it } from 'vitest';

import { composerThreadScopeKey } from './composer-thread-scope-key';

describe('composerThreadScopeKey', () => {
  it('builds a stable workspace+thread key', () => {
    expect(composerThreadScopeKey('workspace_a', 'thread_1')).toBe('workspace_a::thread_1');
  });

  it('returns null when either id is missing', () => {
    expect(composerThreadScopeKey('workspace_a', null)).toBeNull();
    expect(composerThreadScopeKey('', 'thread_1')).toBeNull();
    expect(composerThreadScopeKey(null, null)).toBeNull();
  });
});
