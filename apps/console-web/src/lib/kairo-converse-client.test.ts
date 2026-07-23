import { describe, expect, it } from 'vitest';

import {
  converseTimeoutFallbackReply,
  KAIRO_CONVERSE_DEEP_TIMEOUT_MS,
  KAIRO_CONVERSE_FAST_TIMEOUT_MS,
  resolveKairoConverseTimeoutMs,
} from './kairo-converse-client';

describe('kairo-converse-client timeout policy', () => {
  it('uses a short budget for fast turns and a longer budget for deep', () => {
    expect(resolveKairoConverseTimeoutMs('fast')).toBe(KAIRO_CONVERSE_FAST_TIMEOUT_MS);
    expect(resolveKairoConverseTimeoutMs('deep')).toBe(KAIRO_CONVERSE_DEEP_TIMEOUT_MS);
    expect(resolveKairoConverseTimeoutMs(undefined)).toBe(KAIRO_CONVERSE_FAST_TIMEOUT_MS);
  });

  it('allows an explicit override', () => {
    expect(resolveKairoConverseTimeoutMs('deep', 5000)).toBe(5000);
  });

  it('returns a bounded spoken fallback', () => {
    expect(converseTimeoutFallbackReply(20000)).toContain('20 seconds');
  });
});
