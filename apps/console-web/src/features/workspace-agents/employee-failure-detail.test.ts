import { describe, expect, it } from 'vitest';

import type { CompanyEmployeeRecord } from '../../contracts/canonical';
import {
  agentRuntimeFallbackSpeakDetail,
  employeeResolvedFailureDetail,
  failureSpeakDetail,
  isAgentRuntimeFallbackFailure,
  isAgentSessionInterruptedFailure,
  isOperatorStoppedFailure,
  isRestartInterruptedFailure,
  isRuntimeAuthFailure,
  isShiftContinuationFailure,
  isUsageLimitFailure,
  looksLikeSuccessfulOutcomeDetail,
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
    const authWrapped =
      'Lane B agent fallback reply generated (Cursor rejected CURSOR_API_KEY. Remove or fix the key in /vault, clear it from the control-plane shell env, or run `cursor agent login` to use your subscription.; Cursor Cloud Agent unavailable)';
    expect(normalizeOperatorFailureDetail(authWrapped)).toBe(
      'Cursor rejected CURSOR_API_KEY. Remove or fix the key in /vault, clear it from the control-plane shell env, or run `cursor agent login` to use your subscription.',
    );
  });

  it('detects restart, operator stop, and SIGTERM continuation failures', () => {
    expect(isRestartInterruptedFailure('Run interrupted by control-plane restart')).toBe(true);
    expect(
      isRestartInterruptedFailure('Continuous worker dispatch lost on control-plane restart'),
    ).toBe(true);
    expect(
      isOperatorStoppedFailure('Runtime execution stopped by operator before the CLI finished.'),
    ).toBe(true);
    expect(
      isOperatorStoppedFailure(
        'Lane B agent fallback reply generated (Runtime execution stopped by operator before the CLI finished.)',
      ),
    ).toBe(true);
    expect(isAgentSessionInterruptedFailure('Cursor CLI exited with status 143.')).toBe(true);
    expect(isAgentSessionInterruptedFailure('Cursor CLI exited with status 137.')).toBe(true);
    expect(isAgentSessionInterruptedFailure('Process killed by oom-kill')).toBe(true);
    expect(isShiftContinuationFailure('Cursor CLI exited with status 143.')).toBe(true);
    expect(isShiftContinuationFailure('Cursor CLI exited with status 137.')).toBe(true);
    expect(
      isShiftContinuationFailure(
        'Runtime execution stopped by operator before the CLI finished.',
      ),
    ).toBe(true);
    expect(isShiftContinuationFailure('vitest: assertion failed')).toBe(false);
  });

  it('prefers usage-limit causes over unavailable peers', () => {
    const wrapped =
      "Lane B agent fallback reply generated (Codex CLI (local) unavailable; Running as unit: axon-agent.scope; Invocation ID: abc; ActionRequiredError: You're out of usage.)";
    expect(normalizeOperatorFailureDetail(wrapped)).toMatch(/ActionRequiredError|out of usage/i);
    expect(normalizeOperatorFailureDetail(wrapped)).not.toMatch(/Codex CLI \(local\) unavailable/i);
    expect(isUsageLimitFailure(wrapped)).toBe(true);
    expect(agentRuntimeFallbackSpeakDetail(wrapped)).toMatch(/usage limits blocked/i);
  });

  it('detects usage-limit failures after lane b wrapper normalization', () => {
    const wrapped =
      "Lane B agent fallback reply generated (ActionRequiredError: You're out of usage.)";
    expect(isUsageLimitFailure(wrapped)).toBe(true);
    expect(isUsageLimitFailure('ActionRequiredError: out of usage')).toBe(true);
    expect(
      isUsageLimitFailure(
        'Lane B agent fallback reply generated (ActionRequiredError: Increase limits for faster responses.)',
      ),
    ).toBe(true);
    expect(isUsageLimitFailure('vitest: assertion failed')).toBe(false);
    expect(isUsageLimitFailure('ActionRequiredError')).toBe(false);
    expect(isUsageLimitFailure('ActionRequiredError: Please accept the terms')).toBe(false);
    expect(agentRuntimeFallbackSpeakDetail(wrapped)).toMatch(/usage limits blocked/i);
  });

  it('detects runtime-auth failures after lane b wrapper normalization', () => {
    const wrapped =
      'Lane B agent fallback reply generated (Cursor is installed but not signed in. Run `cursor agent login` or unlock /vault.; Cursor Cloud Agent unavailable; Codex CLI (local) unavailable)';
    expect(isRuntimeAuthFailure(wrapped)).toBe(true);
    expect(normalizeOperatorFailureDetail(wrapped)).toBe(
      'Cursor is installed but not signed in. Run `cursor agent login` or unlock /vault.',
    );
    expect(agentRuntimeFallbackSpeakDetail(wrapped)).toMatch(/runtime auth is not ready/i);
    expect(isRuntimeAuthFailure('vitest: assertion failed')).toBe(false);
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

  it('detects success-like outcome details that should clear failure banners', () => {
    expect(looksLikeSuccessfulOutcomeDetail('Run completed')).toBe(true);
    expect(looksLikeSuccessfulOutcomeDetail('completed')).toBe(true);
    expect(looksLikeSuccessfulOutcomeDetail('succeeded')).toBe(true);
    expect(looksLikeSuccessfulOutcomeDetail('vitest: assertion failed')).toBe(false);
    expect(looksLikeSuccessfulOutcomeDetail('')).toBe(false);
  });
});
