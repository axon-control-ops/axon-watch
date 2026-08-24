import { describe, expect, it } from 'vitest';

import { agentAccessPill } from './agent-access-pill';

const base = { sandboxEnabled: true, toolCapableMode: true };

describe('agent access pill', () => {
  it('reports read-only for a consultative run even with Sandbox on', () => {
    // The watcher case: the pill used to read FULL ACCESS regardless.
    const pill = agentAccessPill({
      ...base,
      policy: { known: true, execution_access: 'consultative', write_paths: [], read_only: true },
    });
    expect(pill.label).toBe('READ-ONLY');
    expect(pill.tone).toBe('read-only');
  });

  it('reports scoped writes for a role-limited fleet worker', () => {
    const pill = agentAccessPill({
      ...base,
      policy: { known: true, execution_access: 'full', write_paths: ['website', 'docs'] },
    });
    expect(pill.label).toBe('SCOPED · 2 paths');
    expect(pill.detail).toContain('website, docs');
  });

  it('still reports full access when the scope is genuinely unrestricted', () => {
    const pill = agentAccessPill({
      ...base,
      policy: { known: true, execution_access: 'full', write_paths: ['.'] },
    });
    expect(pill.label).toBe('FULL ACCESS');
  });

  it('never claims full access before a policy resolves', () => {
    const pill = agentAccessPill({ ...base, policy: null });
    expect(pill.label).toBe('ACCESS PENDING');
    expect(pill.tone).toBe('unknown');
  });

  it('reports read-only for non tool-capable modes', () => {
    const pill = agentAccessPill({ ...base, toolCapableMode: false, policy: null });
    expect(pill.label).toBe('READ-ONLY');
  });

  it('mentions the sandbox only when it is on', () => {
    const on = agentAccessPill({ ...base, policy: { known: true, execution_access: 'full', write_paths: ['.'] } });
    const off = agentAccessPill({ ...base, sandboxEnabled: false, policy: { known: true, execution_access: 'full', write_paths: ['.'] } });
    expect(on.detail).toContain('Sandbox');
    expect(off.detail).not.toContain('Sandbox');
  });
});
