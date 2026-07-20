import { describe, expect, it } from 'vitest';

import {
  companyFailedEmployees,
  companyFailedEmployeesHint,
  companyFailedEmployeesHintTooltip,
  companyHasFailedEmployees,
  companyHasWorkingEmployees,
  companyHeadline,
  employeeDisplayStatus,
  employeeShiftNeedsContinuation,
  employeeDockReceiptDetail,
  employeeDockReceiptRunId,
  employeeDockReceiptRunLabel,
  employeeFailureLine,
  employeeFailureRetryActionLabel,
  employeeFailureDetailTooltip,
  employeeFailurePeekKey,
  employeeFailureBannerCopy,
  employeeFailureBannerAriaLabel,
  employeeFailureBeatAriaLabel,
  employeeGlowTone,
  employeeIsWorking,
  employeeMetaLine,
  adjacentPresenceStripEmployee,
  employeePresenceContextPhrase,
  employeePresenceSelectAriaLabel,
  employeePresenceSelectLabel,
  employeePresenceStripHoverTitle,
  employeePresenceStripTitle,
  firstFailedRosterEmployee,
  pickDefaultRosterEmployee,
  normalizeOperatorFailureDetail,
  presenceStripOptionId,
  selectedPresenceStripEmployee,
  employeeStatusLabel,
  employeeTalkLine,
  employeeSpeakLine,
  sortEmployeesForPresenceStrip,
} from './company-roster-view';
import type { CompanyEmployeeRecord } from '../../contracts/canonical';

function employee(overrides: Partial<CompanyEmployeeRecord> = {}): CompanyEmployeeRecord {
  return {
    employee_id: 'e1',
    workspace_id: 'workspace_demo',
    name: 'Shell Craft',
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

describe('company-roster-view', () => {
  it('formats employee meta and status labels', () => {
    expect(
      employeeMetaLine({
        employee_id: 'e1',
        workspace_id: 'workspace_demo',
        name: 'Rowan',
        role: 'watcher',
        role_label: 'Watcher',
        schedule: 'always_on',
        schedule_label: 'Always on (24/7)',
        status: 'watching',
        owns: 'signals',
        enabled: true,
        primary: false,
      }),
    ).toBe('Always on (24/7)');
    expect(employeeStatusLabel('waiting_approval')).toBe('waiting approval');
    expect(employeeStatusLabel('failed')).toBe('last shift failed');
    expect(employeeStatusLabel('interrupted')).toBe('shift interrupted');
  });

  it('builds company headline with employee count', () => {
    expect(companyHeadline('Axon-X', 5)).toBe('Axon-X · 5 employees');
    expect(companyHeadline('Solo', 1)).toBe('Solo · 1 employee');
  });

  it('surfaces last shift failure detail instead of bare FAILED', () => {
    expect(
      employeeFailureLine(
        employee({
          status: 'idle',
          last_outcome: 'failed',
          last_outcome_detail: 'vitest: assertion failed',
        }),
      ),
    ).toContain('vitest: assertion failed');
    expect(
      employeeFailureBannerCopy(
        employee({
          name: 'Jules',
          status: 'idle',
          last_outcome: 'failed',
          last_outcome_detail: 'vitest: assertion failed',
        }),
      ),
    ).toBe('Jules — Last shift failed: vitest: assertion failed');
    expect(
      employeeFailureBannerAriaLabel(
        employee({
          name: 'Jules',
          status: 'idle',
          last_outcome: 'failed',
          last_outcome_detail: 'vitest: assertion failed',
        }),
      ),
    ).toContain('Jules — Last shift failed: vitest: assertion failed');
    expect(
      employeeTalkLine(
        employee({
          status: 'idle',
          last_outcome: 'failed',
          last_outcome_detail: 'vitest: assertion failed',
        }),
      ),
    ).toContain('Last shift failed');
    expect(
      employeeDisplayStatus(
        employee({
          status: 'idle',
          last_outcome: 'failed',
          last_outcome_detail: 'vitest: assertion failed',
        }),
      ),
    ).toBe('failed');
    expect(employeeStatusLabel(employeeDisplayStatus(employee({ status: 'idle' })))).toBe('idle');
    expect(
      employeeFailureLine(
        employee({
          status: 'executing',
          last_outcome: 'failed',
          last_outcome_detail: 'vitest: assertion failed',
        }),
      ),
    ).toBeNull();
    expect(
      employeeDisplayStatus(
        employee({
          status: 'executing',
          last_outcome: 'failed',
          last_outcome_detail: 'vitest: assertion failed',
        }),
      ),
    ).toBe('executing');
  });

  it('maps usage-limit failures to operator-friendly copy', () => {
    const usageBlocked = employee({
      name: 'Jules',
      status: 'idle',
      last_outcome: 'failed',
      last_outcome_detail:
        "Lane B agent fallback reply generated (ActionRequiredError: Increase limits for faster responses You're out of usage.)",
    });
    const friendlyLine =
      'Last shift could not start — usage limits blocked the agent runtime. Restore limits, then use Retry shift.';
    expect(employeeFailureLine(usageBlocked)).toBe(friendlyLine);
    expect(employeeFailureBannerCopy(usageBlocked)).toBe(`Jules — ${friendlyLine}`);
    expect(employeeFailureBannerAriaLabel(usageBlocked)).toContain('Full detail:');
    expect(employeeFailureBannerAriaLabel(usageBlocked)).toContain('out of usage');
    expect(
      employeeFailureLine(
        employee({
          status: 'idle',
          last_outcome: 'failed',
          last_outcome_detail: 'ActionRequiredError: out of usage',
        }),
      ),
    ).toBe(friendlyLine);
    expect(
      employeeTalkLine(
        employee({
          status: 'idle',
          last_outcome: 'failed',
          last_outcome_detail: 'ActionRequiredError: out of usage',
        }),
      ),
    ).toContain('usage limits blocked the agent runtime');
  });

  it('maps restart-interrupted failures to operator-friendly copy', () => {
    const interrupted = employee({
      status: 'idle',
      last_outcome: 'failed',
      last_outcome_detail: 'Run interrupted by control-plane restart',
      last_run_id: 'run_5c0253a7808a',
    });
    expect(employeeShiftNeedsContinuation(interrupted)).toBe(true);
    expect(employeeDisplayStatus(interrupted)).toBe('interrupted');
    expect(employeeFailureLine(interrupted)).toBe(
      'Last shift interrupted by server restart — use Continue shift to pick up where you left off.',
    );
    expect(employeeSpeakLine(interrupted, 'talk', { talkMode: 'callback', entropy: '1' })).toMatch(
      /server restarted and cut the shift short/i,
    );
    expect(employeeSpeakLine(interrupted, 'talk', { talkMode: 'callback', entropy: '1' })).not.toMatch(
      /control-plane restart/i,
    );
  });

  it('maps agent runtime fallback failures to operator-friendly copy', () => {
    const detail =
      'Lane B agent fallback reply generated (Cursor CLI exited with status 143.; Cursor Cloud Agent unavailable; Codex CLI (local) unavailable; Codex Cloud Task unavailable)';
    const failed = employee({
      name: 'Jules',
      status: 'idle',
      last_outcome: 'failed',
      last_outcome_detail: detail,
      last_run_id: 'run_95ec3ce2d508',
    });
    expect(employeeShiftNeedsContinuation(failed)).toBe(true);
    expect(employeeDisplayStatus(failed)).toBe('interrupted');
    expect(employeeFailureLine(failed)).toBe(
      'Last shift interrupted before it could finish — use Continue shift to pick up where you left off.',
    );
    expect(employeeFailureBannerCopy(failed)).toBe(
      'Jules — Last shift interrupted before it could finish — use Continue shift to pick up where you left off.',
    );
    expect(employeeFailureDetailTooltip(failed)).toBe('Cursor CLI exited with status 143.');
    expect(employeeSpeakLine(failed, 'talk', { talkMode: 'callback', entropy: '1' })).toMatch(
      /agent session was interrupted/i,
    );
    expect(employeeSpeakLine(failed, 'talk', { talkMode: 'callback', entropy: '1' })).not.toMatch(
      /Codex CLI/i,
    );
  });

  it('normalizes lane b fallback wrappers and dispatch prefixes', () => {
    const wrapped =
      'Lane B agent fallback reply generated (CLI runtime timed out after 240s.; Cursor Cloud Agent unavailable; Codex CLI (local) unavailable; Codex Cloud Task unavailable)';
    expect(normalizeOperatorFailureDetail(wrapped)).toBe('CLI runtime timed out after 240s.');
    expect(
      normalizeOperatorFailureDetail('continuous worker dispatch failed: cursor agent unavailable'),
    ).toBe('cursor agent unavailable');
  });

  it('shows normalized api failure detail without lane b wrapper noise', () => {
    const failed = employee({
      name: 'Reed',
      status: 'idle',
      last_outcome: 'failed',
      last_outcome_detail: 'CLI runtime timed out after 240s.',
      last_run_id: 'run_34e5116fecb6',
    });
    expect(employeeShiftNeedsContinuation(failed)).toBe(false);
    expect(employeeDisplayStatus(failed)).toBe('failed');
    expect(employeeFailureLine(failed)).toBe(
      'Last shift failed: CLI runtime timed out after 240s.',
    );
    expect(employeeFailureBannerCopy(failed)).toBe(
      'Reed — Last shift failed: CLI runtime timed out after 240s.',
    );
    expect(employeeSpeakLine(failed, 'talk', { talkMode: 'callback', entropy: '1' })).toMatch(
      /240s/i,
    );
  });

  it('dedupes dock receipt detail when the failure beat already carries it', () => {
    const failed = employee({
      status: 'idle',
      last_outcome: 'failed',
      last_outcome_detail: 'vitest: assertion failed',
      last_run_id: 'run_failed_1',
    });
    expect(employeeDockReceiptDetail(failed)).toBeNull();
    expect(employeeDockReceiptRunId(failed)).toBe('run_failed_1');
    expect(employeeDockReceiptRunLabel('run_failed_1')).toBe('#failed');

    const ok = employee({
      status: 'idle',
      last_outcome: 'completed',
      last_outcome_detail: 'Shipped dock polish with receipts.',
      last_run_id: 'run_ok_1',
    });
    expect(employeeDockReceiptDetail(ok)).toBe('Shipped dock polish with receipts.');
    expect(employeeDockReceiptRunId(ok)).toBe('run_ok_1');
    expect(employeeDockReceiptRunLabel('run_ok_1')).toBe('#ok_1');
  });

  it('steps presence strip selection with keyboard moves', () => {
    const rows = [
      employee({ employee_id: 'e_idle', name: 'Zara', status: 'idle' }),
      employee({
        employee_id: 'e_failed',
        name: 'Mira',
        status: 'idle',
        last_outcome: 'failed',
        last_outcome_detail: 'timeout',
      }),
      employee({ employee_id: 'e_work', name: 'Alex', status: 'executing' }),
    ];
    const sorted = sortEmployeesForPresenceStrip(rows);
    expect(adjacentPresenceStripEmployee(rows, null, 'first')?.employee_id).toBe(
      sorted[0].employee_id,
    );
    expect(adjacentPresenceStripEmployee(rows, sorted[0].employee_id, 'next')?.employee_id).toBe(
      sorted[1].employee_id,
    );
    expect(adjacentPresenceStripEmployee(rows, sorted[0].employee_id, 'prev')?.employee_id).toBe(
      sorted[sorted.length - 1].employee_id,
    );
    expect(adjacentPresenceStripEmployee(rows, sorted[1].employee_id, 'last')?.employee_id).toBe(
      sorted[sorted.length - 1].employee_id,
    );
  });

  it('picks default roster selection with failed teammates first in strip order', () => {
    const rows = [
      employee({ employee_id: 'e_idle', name: 'Zara', status: 'idle' }),
      employee({
        employee_id: 'e_failed_b',
        name: 'Bravo',
        status: 'idle',
        last_outcome: 'failed',
        last_outcome_detail: 'build failed',
      }),
      employee({
        employee_id: 'e_failed_a',
        name: 'Alpha',
        status: 'idle',
        last_outcome: 'failed',
        last_outcome_detail: 'timeout',
      }),
      employee({ employee_id: 'e_lead', name: 'Lead', role: 'lead', primary: true, status: 'idle' }),
    ];
    expect(firstFailedRosterEmployee(rows)?.employee_id).toBe('e_failed_a');
    expect(pickDefaultRosterEmployee(rows)?.employee_id).toBe('e_failed_a');
    expect(pickDefaultRosterEmployee([rows[0], rows[3]])?.employee_id).toBe('e_lead');
    expect(pickDefaultRosterEmployee([rows[0]])?.employee_id).toBe('e_idle');
  });

  it('sorts presence strip with failed teammates first', () => {
    const rows = [
      employee({ employee_id: 'e_idle', name: 'Zara', status: 'idle' }),
      employee({
        employee_id: 'e_failed',
        name: 'Mira',
        status: 'idle',
        last_outcome: 'failed',
        last_outcome_detail: 'timeout',
      }),
      employee({ employee_id: 'e_work', name: 'Alex', status: 'executing' }),
      employee({ employee_id: 'e_lead', name: 'Lead', role: 'lead', primary: true, status: 'idle' }),
    ];
    expect(
      sortEmployeesForPresenceStrip(rows).map((row) => row.employee_id),
    ).toEqual(['e_failed', 'e_work', 'e_lead', 'e_idle']);
  });

  it('builds stable presence strip option ids', () => {
    expect(presenceStripOptionId('e_failed')).toBe('company-presence-option-e_failed');
    expect(presenceStripOptionId('')).toBe('');
    expect(presenceStripOptionId(null)).toBe('');
  });

  it('builds presence strip aria labels and titles for failure, pause, and live shifts', () => {
    const failed = employee({
      name: 'Jules',
      status: 'idle',
      last_outcome: 'failed',
      last_outcome_detail: 'timeout',
    });
    expect(employeePresenceContextPhrase(failed)).toBe('Last shift failed: timeout');
    expect(employeePresenceSelectLabel(failed)).toBe(
      'Select Jules, Last shift failed: timeout',
    );
    expect(employeePresenceStripTitle(failed)).toBe('Jules — Last shift failed: timeout');
    expect(employeePresenceSelectLabel(employee({ name: 'Jules', enabled: false }))).toBe(
      'Select Jules, paused',
    );
    expect(employeePresenceStripTitle(employee({ name: 'Jules', enabled: false }))).toBe(
      'Jules — Paused',
    );
    const working = employee({ name: 'Alex', status: 'executing' });
    expect(employeePresenceContextPhrase(working)).toBe('executing');
    expect(employeePresenceSelectLabel(working)).toBe('Select Alex, executing');
    expect(employeePresenceStripTitle(working)).toBe('Alex — executing');
    expect(employeePresenceSelectLabel(employee({ name: 'Jules' }))).toBe('Select Jules');
    expect(employeePresenceStripTitle(employee({ name: 'Jules' }))).toBe('Jules');
  });

  it('resolves the selected presence strip employee for keyboard confirm', () => {
    const rows = [
      employee({ employee_id: 'e_idle', name: 'Zara' }),
      employee({ employee_id: 'e_failed', name: 'Mira', last_outcome: 'failed' }),
    ];
    expect(selectedPresenceStripEmployee(rows, 'e_failed')?.name).toBe('Mira');
    expect(selectedPresenceStripEmployee(rows, 'missing')).toBeNull();
    expect(selectedPresenceStripEmployee(rows, null)).toBeNull();
  });

  it('truncates very long failure detail in the talk banner', () => {
    const longDetail = `${'vitest: '.repeat(20)}assertion failed`;
    const line = employeeFailureLine(
      employee({
        status: 'idle',
        last_outcome: 'failed',
        last_outcome_detail: longDetail,
      }),
    );
    expect(line).toContain('Last shift failed:');
    expect(line!.length).toBeLessThan(longDetail.length + 24);
    expect(line).toMatch(/…$/);
  });

  it('exposes full failure detail for tooltips when the banner line is truncated', () => {
    const longDetail = `${'ActionRequiredError: '.repeat(20)}out of usage`;
    const row = employee({
      status: 'idle',
      last_outcome: 'failed',
      last_outcome_detail: longDetail,
    });
    expect(employeeFailureDetailTooltip(row)).toBe(longDetail);
    expect(employeeFailureDetailTooltip(employee({ status: 'executing', last_outcome: 'failed' }))).toBeUndefined();
    expect(employeeFailureBannerAriaLabel(row)).toContain('Full detail:');
    expect(employeeFailureBannerAriaLabel(row)).toContain(longDetail);
    expect(employeeFailureBeatAriaLabel(row)).toContain('Full detail:');
    expect(employeeFailureBeatAriaLabel(row)).toContain(longDetail);
    expect(employeePresenceStripHoverTitle(row)).toBe(longDetail);
    expect(employeePresenceSelectAriaLabel(row)).toContain('Full detail:');
    expect(employeePresenceSelectAriaLabel(row)).toContain(longDetail);
  });

  it('keeps short failure labels compact for hover and screen readers', () => {
    const row = employee({
      name: 'Jules',
      status: 'idle',
      last_outcome: 'failed',
      last_outcome_detail: 'timeout',
    });
    expect(employeePresenceStripHoverTitle(row)).toBe('Jules — Last shift failed: timeout');
    expect(employeePresenceSelectAriaLabel(row)).toBe('Select Jules, Last shift failed: timeout');
    expect(employeeFailureBeatAriaLabel(row)).toBe('Last shift failed: timeout');
  });

  it('uses failure-aware callback speak when idle after a failed shift', () => {
    const failed = employee({
      status: 'idle',
      last_outcome: 'failed',
      last_outcome_detail: 'vitest: assertion failed',
    });
    const line = employeeSpeakLine(failed, 'talk', { talkMode: 'callback', entropy: '1' });
    expect(line).toMatch(/failed|retry/i);
    expect(line).toContain('vitest: assertion failed');
    expect(line).not.toMatch(/Present\.|Yes\?/);
  });

  it('speaks a real role briefing instead of Present stubs', () => {
    const bridge = employee({
      name: 'Bridge',
      role: 'integrations',
      role_label: 'Integrations Engineer',
      owns: 'connectors, watch service, and cross-repo wiring',
      status: 'idle',
      last_outcome: 'failed',
      last_outcome_detail: 'cursor agent unavailable',
    });
    const talk = employeeSpeakLine(bridge, 'talk', { talkMode: 'intro' });
    expect(talk).toContain('Bridge');
    expect(talk).toContain('connectors');
    expect(talk).toContain('cursor agent unavailable');
    expect(talk).not.toMatch(/Present\.|On deck\.|Ready to help/);

    const status = employeeSpeakLine(bridge, 'status');
    expect(status).toContain('reporting in');
    expect(status).toContain('cursor agent unavailable');
    expect(status).toMatch(/retry|receipts/i);
  });

  it('detects failed teammates for roster alerts', () => {
    expect(
      companyHasFailedEmployees([
        employee({ status: 'idle' }),
        employee({
          employee_id: 'e2',
          status: 'idle',
          last_outcome: 'failed',
          last_outcome_detail: 'timeout',
        }),
      ]),
    ).toBe(true);
    expect(
      companyHasFailedEmployees([
        employee({ status: 'executing', last_outcome: 'failed', last_outcome_detail: 'timeout' }),
      ]),
    ).toBe(false);
    expect(
      companyFailedEmployees([
        employee({ status: 'idle' }),
        employee({
          employee_id: 'e2',
          status: 'idle',
          last_outcome: 'failed',
          last_outcome_detail: 'timeout',
        }),
        employee({
          employee_id: 'e3',
          status: 'idle',
          last_outcome: 'failed',
          last_outcome_detail: 'build failed',
        }),
      ]),
    ).toHaveLength(2);
  });

  it('builds failure hints with teammate names and counts', () => {
    expect(companyFailedEmployeesHint([])).toBeNull();
    expect(
      companyFailedEmployeesHint([
        employee({
          name: 'Shell Craft',
          status: 'idle',
          last_outcome: 'failed',
          last_outcome_detail: 'vitest',
        }),
      ]),
    ).toBe('Shell Craft — Last shift failed: vitest');
    expect(
      companyFailedEmployeesHint([
        employee({
          name: 'Jules',
          status: 'idle',
          last_outcome: 'failed',
          last_outcome_detail: 'Run interrupted by control-plane restart',
        }),
      ]),
    ).toBe(
      'Jules — Last shift interrupted by server restart — use Continue shift to pick up where you left off.',
    );
    expect(
      companyFailedEmployeesHint([
        employee({
          name: 'Jules',
          status: 'idle',
          last_outcome: 'failed',
          last_outcome_detail:
            'Lane B agent fallback reply generated (Cursor CLI exited with status 143.; Cursor Cloud Agent unavailable)',
        }),
      ]),
    ).toBe(
      'Jules — Last shift interrupted before it could finish — use Continue shift to pick up where you left off.',
    );
    expect(
      companyFailedEmployeesHint([
        employee({
          employee_id: 'e2',
          name: 'Night Watch',
          status: 'idle',
          last_outcome: 'failed',
          last_outcome_detail: 'timeout',
        }),
        employee({
          employee_id: 'e3',
          name: 'Backend Smith',
          status: 'idle',
          last_outcome: 'failed',
          last_outcome_detail: 'build failed',
        }),
      ]),
    ).toBe(
      '2 teammates need attention after a failed shift — select one for Retry shift, or click to talk it through.',
    );
  });

  it('exposes full failure detail on roster alert hint hover when truncated', () => {
    const longDetail = `${'ActionRequiredError: '.repeat(20)}out of usage`;
    const row = employee({
      name: 'Jules',
      status: 'idle',
      last_outcome: 'failed',
      last_outcome_detail: longDetail,
    });
    expect(companyFailedEmployeesHintTooltip([row])).toBe(`Jules — ${longDetail}`);
    expect(companyFailedEmployeesHintTooltip([row, employee({ employee_id: 'e2', last_outcome: 'failed' })])).toBeNull();
    expect(
      companyFailedEmployeesHintTooltip([
        employee({
          status: 'idle',
          last_outcome: 'failed',
          last_outcome_detail: 'timeout',
        }),
      ]),
    ).toBeNull();
  });

  it('builds stable peek keys for auto-expanding the agent dock after a failed shift', () => {
    expect(
      employeeFailurePeekKey(
        employee({
          status: 'idle',
          last_outcome: 'failed',
          last_outcome_detail: 'timeout',
          last_run_id: 'run_abc',
        }),
      ),
    ).toBe('e1:run_abc');
    expect(
      employeeFailurePeekKey(
        employee({
          status: 'idle',
          last_outcome: 'failed',
          last_outcome_detail: 'timeout',
        }),
      ),
    ).toBe('e1:timeout');
    expect(employeeFailurePeekKey(employee({ status: 'idle' }))).toBeNull();
  });

  it('maps working status, glow tone, and talk lines', () => {
    expect(employeeIsWorking('idle')).toBe(false);
    expect(employeeIsWorking('executing')).toBe(true);
    expect(employeeGlowTone(employee({ role: 'backend' }))).toBe('backend');
    expect(employeeGlowTone(employee({ role: 'lead', primary: true }))).toBe('lead');
    expect(employeeTalkLine(employee({ status: 'idle' }))).toBeNull();
    expect(employeeTalkLine(employee({ status: 'executing' }))).toContain('In progress');
    expect(employeeSpeakLine(employee({ status: 'idle' }), 'talk')).toContain('Shell');
    expect(employeeSpeakLine(employee({ status: 'idle' }), 'talk')).toContain('What do you need');
    expect(employeeSpeakLine(employee({ status: 'executing' }), 'talk', { talkMode: 'intro' })).toContain(
      'Shell',
    );
    expect(employeeSpeakLine(employee({ status: 'idle' }), 'talk', { talkMode: 'callback' })).toMatch(
      /Shell|checking in|you called/i,
    );
    expect(
      employeeSpeakLine(employee({ status: 'executing' }), 'talk', {
        talkMode: 'callback',
        entropy: '1',
      }),
    ).toMatch(/still mid-|in flight|live on|listening/i);
    expect(
      companyHasWorkingEmployees([
        employee({ status: 'idle' }),
        employee({ employee_id: 'e2', status: 'watching' }),
      ]),
    ).toBe(true);
  });
});
