import { describe, expect, it } from 'vitest';

import {
  SANDBOX_SESSION_CONSENT_LINES,
  sandboxSessionHint,
  sandboxSessionLabel,
} from './sandbox-session-view';

describe('sandbox session view', () => {
  it('exposes consent lines for the enable dialog', () => {
    expect(SANDBOX_SESSION_CONSENT_LINES.length).toBeGreaterThanOrEqual(2);
  });

  it('labels and hints reflect on/off and env force', () => {
    expect(sandboxSessionLabel(false)).toBe('Sandbox');
    expect(sandboxSessionLabel(true)).toBe('Sandbox · On');
    expect(sandboxSessionHint(false, false).toLowerCase()).toContain('enable');
    expect(sandboxSessionHint(true, false).toLowerCase()).toContain('on');
    expect(sandboxSessionHint(true, true).toLowerCase()).toContain('forced');
  });
});
