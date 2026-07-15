import { describe, expect, it } from 'vitest';

import { resolveSttCaptureMode } from './kairo-cloud-stt';

describe('resolveSttCaptureMode', () => {
  it('blocks when privacy is on', () => {
    expect(resolveSttCaptureMode('cloud', true)).toBe('blocked');
  });

  it('maps continuous and default browser modes', () => {
    expect(resolveSttCaptureMode('browser_continuous', false)).toBe('browser_continuous');
    expect(resolveSttCaptureMode('cloud', false)).toBe('browser');
    expect(resolveSttCaptureMode('browser', false)).toBe('browser');
  });
});
