import { describe, expect, it } from 'vitest';

import {
  buildCompanyRosterAlertBadge,
  companyFailedEmployees,
  companyFailedEmployeesHint,
  companyFailedEmployeesHintTooltip,
  companyHasFailedEmployees,
  employeeDisplayStatus,
  employeeDockReceiptDetail,
  employeeFailureBannerAriaLabel,
  employeeFailureBannerCopy,
  employeeFailureBeatAriaLabel,
  employeeFailureDetailTooltip,
  employeeFailureLine,
  employeeFailurePeekKey,
  employeeFailureRetryActionLabel,
  employeeShiftNeedsContinuation,
} from './company-roster-failure-view';
import {
  employeePresenceSelectAriaLabel,
  employeePresenceStripHoverTitle,
  employeeSpeakLine,
  employeeStatusLabel,
  employeeTalkLine,
  normalizeOperatorFailureDetail,
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

describe('company-roster-failure-view', () => {
  it('hides stale failures while the teammate is live-busy in IDE', () => {
    const failed = employee({
      status: 'idle',
      last_outcome: 'failed',
      last_outcome_detail:
        'Critical Review Clause missing: final reply must end with Confidence: N/10',
    });
    expect(employeeFailureLine(failed)).toContain('closing Confidence line was missing');
    expect(employeeFailureLine(failed, { liveBusy: true })).toBeNull();
    expect(companyFailedEmployees([failed], [failed.employee_id])).toEqual([]);
    expect(companyHasFailedEmployees([failed], [failed.employee_id])).toBe(false);
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
    ).toBe('Jules — Last job failed: vitest: assertion failed');
    expect(
      employeeFailureBannerAriaLabel(
        employee({
          name: 'Jules',
          status: 'idle',
          last_outcome: 'failed',
          last_outcome_detail: 'vitest: assertion failed',
        }),
      ),
    ).toContain('Jules — Last job failed: vitest: assertion failed');
    expect(
      employeeTalkLine(
        employee({
          status: 'idle',
          last_outcome: 'failed',
          last_outcome_detail: 'vitest: assertion failed',
        }),
      ),
    ).toContain('Last job failed');
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
      'Last job hit a Cursor usage signal — Auto+Composer may still have headroom or on-demand spend. Check Usage in Settings → CLI runtime, then Try again.';
    expect(employeeFailureLine(usageBlocked)).toBe(friendlyLine);
    expect(employeeFailureBannerCopy(usageBlocked)).toBe(`Jules — ${friendlyLine}`);
    expect(employeeFailureBannerAriaLabel(usageBlocked)).toContain('Full detail:');
    expect(employeeFailureBannerAriaLabel(usageBlocked)).toMatch(/usage signal|Auto\+Composer|on-demand/i);
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
    ).toMatch(/usage/i);
  });

  it('maps completion-gate failures to operator-friendly copy', () => {
    const sorenLike = employee({
      name: 'Soren',
      role: 'integrations',
      status: 'idle',
      last_outcome: 'failed',
      last_outcome_detail:
        'Workspace delivery blocked by completion gate: Implementation requested but worker produced no changed files',
    });
    expect(employeeFailureLine(sorenLike)).toBe(
      'Last job produced no file changes in the worker isolation checkout — not Composer Sandbox. Tap Try again with a narrower task, or reassign as report-only audit.',
    );
    expect(employeeDisplayStatus(sorenLike)).toBe('failed');
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
      'Last job was interrupted when the server restarted — tap Continue to pick up where they left off.',
    );
    expect(employeeSpeakLine(interrupted, 'talk', { talkMode: 'callback', entropy: '1' })).toMatch(
      /server restarted and cut the shift short/i,
    );
    expect(employeeSpeakLine(interrupted, 'talk', { talkMode: 'callback', entropy: '1' })).not.toMatch(
      /control-plane restart/i,
    );
  });

  it('maps OOM/SIGKILL interruptions to a memory-headroom message', () => {
    const oom = employee({
      status: 'idle',
      last_outcome: 'failed',
      last_outcome_detail: 'Cursor CLI exited with status 137.',
      last_run_id: 'run_oom137',
    });
    expect(employeeFailureLine(oom)).toBe(
      'Last job was stopped to free memory — tap Continue when the machine has headroom.',
    );
  });

  it('maps runtime-auth failures to operator-friendly copy', () => {
    const authBlocked = employee({
      name: 'Rowan',
      role: 'watcher',
      status: 'idle',
      last_outcome: 'failed',
      last_outcome_detail:
        'Lane B agent fallback reply generated (Cursor is installed but not signed in. Run `cursor agent login` or unlock /vault.; Cursor Cloud Agent unavailable)',
      last_run_id: 'run_43ca086d22d4',
    });
    const friendlyLine =
      'Last job could not run — login is not ready. Run `cursor agent login` on the host or unlock /vault, then tap Try again.';
    expect(employeeFailureLine(authBlocked)).toBe(friendlyLine);
    expect(employeeFailureBannerCopy(authBlocked)).toBe(`Rowan — ${friendlyLine}`);
    expect(
      employeeSpeakLine(authBlocked, 'talk', { talkMode: 'callback', entropy: '1' }),
    ).toMatch(/runtime auth is not ready/i);
  });

  it('maps Cursor auth probe timeouts to runtime-auth friendly copy', () => {
    const probeTimedOut = employee({
      name: 'Priya',
      role: 'frontend',
      status: 'idle',
      last_outcome: 'failed',
      last_outcome_detail:
        'Lane B agent fallback reply generated (Cursor auth probe timed out. Run `cursor agent status` manually.; Cursor Cloud Agent unavailable)',
      last_run_id: 'run_auth_probe',
    });
    const friendlyLine =
      'Last job could not run — Cursor CLI auth timed out. Check runtime on the host, then tap Try again.';
    expect(employeeFailureLine(probeTimedOut)).toBe(friendlyLine);
    expect(employeeFailureDetailTooltip(probeTimedOut)).toContain('auth timed out');
    expect(employeeFailureDetailTooltip(probeTimedOut)).not.toContain('Lane B');
  });

  it('maps operator-stopped failures to operator-friendly copy', () => {
    const stopped = employee({
      name: 'Quinn',
      role: 'integrations',
      status: 'idle',
      last_outcome: 'failed',
      last_outcome_detail:
        'Runtime execution stopped by operator before the CLI finished.',
      last_run_id: 'run_51016bedcba4',
    });
    const friendlyLine =
      'Last job was stopped early — tap Continue to pick up where they left off.';
    expect(employeeShiftNeedsContinuation(stopped)).toBe(true);
    expect(employeeDisplayStatus(stopped)).toBe('interrupted');
    expect(employeeFailureLine(stopped)).toBe(friendlyLine);
    expect(employeeFailureBannerCopy(stopped)).toBe(`Quinn — ${friendlyLine}`);
    expect(employeeFailureRetryActionLabel(stopped)).toBe('Continue');
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
      'Last job was interrupted before it could finish — tap Continue to pick up where they left off.',
    );
    expect(employeeFailureBannerCopy(failed)).toBe(
      'Jules — Last job was interrupted before it could finish — tap Continue to pick up where they left off.',
    );
    expect(employeeFailureDetailTooltip(failed)).toBe('Cursor CLI exited with status 143.');
    expect(employeeSpeakLine(failed, 'talk', { talkMode: 'callback', entropy: '1' })).toMatch(
      /agent session was interrupted/i,
    );
    expect(employeeSpeakLine(failed, 'talk', { talkMode: 'callback', entropy: '1' })).not.toMatch(
      /Codex CLI/i,
    );
  });

  it('labels recovery actions as continue vs retry by failure kind', () => {
    const interrupted = employee({
      status: 'idle',
      last_outcome: 'failed',
      last_outcome_detail: 'Run interrupted by control-plane restart',
    });
    const failed = employee({
      status: 'idle',
      last_outcome: 'failed',
      last_outcome_detail: 'vitest assertion failed',
    });
    expect(employeeFailureRetryActionLabel(interrupted)).toBe('Continue');
    expect(employeeFailureRetryActionLabel(failed)).toBe('Try again');
    expect(employeeFailureRetryActionLabel(employee({ status: 'idle' }))).toBe('Try again');
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
      'Last job failed: CLI runtime timed out after 240s.',
    );
    expect(employeeFailureBannerCopy(failed)).toBe(
      'Reed — Last job failed: CLI runtime timed out after 240s.',
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

    const ok = employee({
      status: 'idle',
      last_outcome: 'completed',
      last_outcome_detail: 'Shipped dock polish with receipts.',
      last_run_id: 'run_ok_1',
    });
    expect(employeeDockReceiptDetail(ok)).toBe('Shipped dock polish with receipts.');
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
    expect(line).toContain('Last job failed:');
    expect(line!.length).toBeLessThan(longDetail.length + 24);
    expect(line).toMatch(/…$/);
  });

  it('exposes full failure detail for tooltips when the banner line is truncated', () => {
    const longDetail = `${'verify:contracts assertion failed — '.repeat(8)}end`;
    const row = employee({
      status: 'idle',
      last_outcome: 'failed',
      last_outcome_detail: longDetail,
    });
    expect(employeeFailureDetailTooltip(row)).toBe(longDetail.replace(/\s+/g, ' ').trim());
    expect(
      employeeFailureDetailTooltip(employee({ status: 'executing', last_outcome: 'failed' })),
    ).toBeUndefined();
    expect(employeeFailureBannerAriaLabel(row)).toContain('Full detail:');
    expect(employeeFailureBannerAriaLabel(row)).toContain('verify:contracts');
    expect(employeeFailureBeatAriaLabel(row)).toContain('Full detail:');
    expect(employeeFailureBeatAriaLabel(row)).toContain('verify:contracts');
    expect(employeePresenceStripHoverTitle(row)).toContain('verify:contracts');
    expect(employeePresenceSelectAriaLabel(row)).toContain('Full detail:');
    expect(employeePresenceSelectAriaLabel(row)).toContain('verify:contracts');
  });

  it('uses operator-friendly tooltips for usage-limit failures', () => {
    const row = employee({
      status: 'idle',
      last_outcome: 'failed',
      last_outcome_detail: `${'ActionRequiredError: '.repeat(20)}out of usage`,
    });
    expect(employeeFailureDetailTooltip(row)).toBe(
      'Cursor usage signal on this shift — Auto+Composer may still have headroom or on-demand spend. Check Usage, then retry.',
    );
  });

  it('keeps short failure labels compact for hover and screen readers', () => {
    const row = employee({
      name: 'Jules',
      status: 'idle',
      last_outcome: 'failed',
      last_outcome_detail: 'timeout',
    });
    expect(employeePresenceStripHoverTitle(row)).toBe('Jules — Last job failed: timeout');
    expect(employeePresenceSelectAriaLabel(row)).toBe('Select Jules, Last job failed: timeout');
    expect(employeeFailureBeatAriaLabel(row)).toBe('Last job failed: timeout');
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
    ).toBe(
      'Shell Craft — Last job failed: vitest Tap to open their dock and Try again.',
    );
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
      'Jules — Last job was interrupted when the server restarted — tap Continue to pick up where they left off.',
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
      'Jules — Last job was interrupted before it could finish — tap Continue to pick up where they left off.',
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
      '2 teammates need attention after a failed job — tap to open a failed teammate\'s dock and Try again.',
    );
  });

  it('exposes full failure detail on roster alert hint hover when truncated', () => {
    const longDetail = `${'verify:contracts assertion failed — '.repeat(8)}end`;
    const row = employee({
      name: 'Jules',
      status: 'idle',
      last_outcome: 'failed',
      last_outcome_detail: longDetail,
    });
    const normalized = longDetail.replace(/\s+/g, ' ').trim();
    expect(companyFailedEmployeesHintTooltip([row])).toBe(`Jules — ${normalized}`);
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

  it('builds stable peek keys for auto-expanding the agent dock after a failed job', () => {
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

  describe('buildCompanyRosterAlertBadge', () => {
    it('returns null when every teammate is healthy', () => {
      expect(buildCompanyRosterAlertBadge([employee({ status: 'idle' })])).toBeNull();
    });

    it('labels a single interrupted job distinctly from a hard failure', () => {
      expect(
        buildCompanyRosterAlertBadge([
          employee({
            status: 'idle',
            last_outcome: 'failed',
            last_outcome_detail: 'Run interrupted by control-plane restart',
          }),
        ]),
      ).toMatchObject({
        label: '1 interrupted',
        tone: 'interrupted',
      });
      expect(
        buildCompanyRosterAlertBadge([
          employee({
            status: 'idle',
            last_outcome: 'failed',
            last_outcome_detail: 'timeout',
          }),
        ]),
      ).toMatchObject({
        label: '1 failed',
        tone: 'failure',
      });
    });

    it('uses mixed attention copy when failures and interruptions overlap', () => {
      expect(
        buildCompanyRosterAlertBadge([
          employee({
            employee_id: 'e1',
            status: 'idle',
            last_outcome: 'failed',
            last_outcome_detail: 'Run interrupted by control-plane restart',
          }),
          employee({
            employee_id: 'e2',
            status: 'idle',
            last_outcome: 'failed',
            last_outcome_detail: 'timeout',
          }),
        ]),
      ).toMatchObject({
        label: '2 need attention',
        tone: 'mixed',
      });
      expect(
        buildCompanyRosterAlertBadge([
          employee({
            employee_id: 'e1',
            status: 'idle',
            last_outcome: 'failed',
            last_outcome_detail: 'Run interrupted by control-plane restart',
          }),
          employee({
            employee_id: 'e2',
            status: 'idle',
            last_outcome: 'failed',
            last_outcome_detail:
              'Runtime execution stopped by operator before the CLI finished.',
          }),
        ]),
      ).toMatchObject({
        label: '2 interrupted',
        tone: 'interrupted',
      });
    });
  });
});
