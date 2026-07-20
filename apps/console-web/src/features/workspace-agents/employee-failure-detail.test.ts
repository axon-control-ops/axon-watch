import { describe, expect, it } from 'vitest';

import type { CompanyEmployeeRecord } from '../../contracts/canonical';
import {
  agentRuntimeFallbackSpeakDetail,
  employeeResolvedFailureDetail,
  failureSpeakDetail,
  isAgentRuntimeFallbackFailure,
  isAgentSessionInterruptedFailure,
  isRestartInterruptedFailure,
  isShiftContinuationFailure,
  isUsageLimitFailure,
  normalizeOperatorFailureDetail,
} from './employee-failure-detail';

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

describe('employee-failure-detail', () => {
  it('normalizes lane b fallback wrappers and dispatch prefixes', () => {
    const wrapped =
      'Lane B agent fallback reply generated (CLI runtime timed out after 240s.; Cursor Cloud Agent unavailable)';
    expect(normalizeOperatorFailureDetail(wrapped)).toBe('CLI runtime timed out after 240s.');
    expect(
      normalizeOperatorFailureDetail('continuous worker dispatch failed: cursor agent unavailable'),
    ).toBe('cursor agent unavailable');
  });

  it('detects restart and SIGTERM continuation failures', () => {
    expect(isRestartInterruptedFailure('Run interrupted by control-plane restart')).toBe(true);
    expect(isAgentSessionInterruptedFailure('Cursor CLI exited with status 143.')).toBe(true);
    expect(isShiftContinuationFailure('Cursor CLI exited with status 143.')).toBe(true);
    expect(isShiftContinuationFailure('vitest: assertion failed')).toBe(false);
  });

  it('detects usage-limit failures after lane b wrapper normalization', () => {
    const wrapped =
      "Lane B agent fallback reply generated (ActionRequiredError: You're out of usage.)";
    expect(isUsageLimitFailure(wrapped)).toBe(true);
    expect(isUsageLimitFailure('ActionRequiredError: out of usage')).toBe(true);
    expect(isUsageLimitFailure('vitest: assertion failed')).toBe(false);
    expect(agentRuntimeFallbackSpeakDetail(wrapped)).toMatch(/usage limits blocked/i);
  });

  it('maps runtime fallback receipts to operator-friendly speak detail', () => {
    const wrapped =
      'Lane B agent fallback reply generated (Cursor CLI exited with status 143.; Cursor Cloud Agent unavailable)';
    expect(isAgentRuntimeFallbackFailure(wrapped)).toBe(true);
    expect(agentRuntimeFallbackSpeakDetail(wrapped)).toMatch(/agent session was interrupted/i);
    expect(failureSpeakDetail(employee({ last_outcome_detail: wrapped }))).toMatch(
      /agent session was interrupted/i,
    );
  });

  it('resolves employee failure detail through normalization', () => {
    expect(
      employeeResolvedFailureDetail(
        employee({
          last_outcome_detail:
            'Lane B agent fallback reply generated (Cursor CLI exited with status 143.)',
        }),
      ),
    ).toBe('Cursor CLI exited with status 143.');
  });
});
