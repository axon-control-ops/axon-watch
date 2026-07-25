import { describe, expect, it } from 'vitest';

import type { CompanyEmployeeRecord } from '../../contracts/canonical';

import { employeeSpeakLine } from './company-roster-speak-view';

function employee(overrides: Partial<CompanyEmployeeRecord> = {}): CompanyEmployeeRecord {
  return {
    employee_id: 'e1',
    workspace_id: 'workspace_demo',
    name: 'Jules',
    role: 'frontend',
    role_label: 'UI/UX',
    schedule: 'continuous',
    schedule_label: 'Continuous',
    status: 'idle',
    owns: 'console UI/UX, dock, and shell polish',
    enabled: true,
    primary: false,
    ...overrides,
  };
}

describe('employeeSpeakLine', () => {
  it('uses role voice hooks instead of generic Present stubs', () => {
    const talk = employeeSpeakLine(employee(), 'talk', { talkMode: 'intro' });
    expect(talk).toContain('Jules');
    expect(talk).toContain('console UI and dock');
    expect(talk).not.toMatch(/Present\.|On deck\.|Ready to help/);

    const status = employeeSpeakLine(employee(), 'status');
    expect(status).toContain('reporting in');
    expect(status).toContain('console UI and dock');
  });

  it('speaks failure-aware intro and callback lines', () => {
    const failed = employee({
      status: 'idle',
      last_outcome: 'failed',
      last_outcome_detail: 'vitest: assertion failed',
    });

    const intro = employeeSpeakLine(failed, 'talk', { talkMode: 'intro' });
    expect(intro).toContain('vitest: assertion failed');
    expect(intro).toMatch(/retry|Retry shift/i);

    const callback = employeeSpeakLine(failed, 'talk', { talkMode: 'callback', entropy: '1' });
    expect(callback).toMatch(/failed|retry/i);
    expect(callback).toContain('vitest: assertion failed');
  });

  it('varies callback lines by entropy while staying stable for the same seed', () => {
    const working = employee({ status: 'executing' });
    const a = employeeSpeakLine(working, 'talk', { talkMode: 'callback', entropy: 'seed-a' });
    const b = employeeSpeakLine(working, 'talk', { talkMode: 'callback', entropy: 'seed-b' });
    expect(a).toMatch(/Jules|mid-|in flight|live on|listening/i);
    expect(a).not.toBe(b);
  });

  it('explains paused teammates cannot take continuous shifts', () => {
    const paused = employee({ enabled: false });
    expect(employeeSpeakLine(paused, 'talk', { talkMode: 'intro' })).toMatch(/paused/i);
    expect(employeeSpeakLine(paused, 'status')).toMatch(/paused/i);
  });
});
