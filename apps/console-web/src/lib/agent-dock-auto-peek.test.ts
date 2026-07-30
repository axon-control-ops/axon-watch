import { describe, expect, it } from 'vitest';

import {
  shouldAutoPeekAgentDock,
  shouldAutoPeekAgentDockForEmployeeFailure,
  shouldAutoPeekAgentDockForRun,
  shouldAutoPeekAgentDockForStreaming,
} from './agent-dock-auto-peek';

describe('shouldAutoPeekAgentDock', () => {
  const base = {
    layoutMode: 'ide' as const,
    agentDockCollapsed: true,
    pendingApprovals: 1,
    lastPeekedApprovalCount: 0,
  };

  it('opens the dock when approvals increase in IDE mode', () => {
    expect(shouldAutoPeekAgentDock(base)).toBe(true);
    expect(
      shouldAutoPeekAgentDock({
        ...base,
        pendingApprovals: 2,
        lastPeekedApprovalCount: 1,
      }),
    ).toBe(true);
  });

  it('does not reopen for the same approval count after a peek', () => {
    expect(
      shouldAutoPeekAgentDock({
        ...base,
        lastPeekedApprovalCount: 1,
      }),
    ).toBe(false);
  });

  it('ignores operator layout and expanded dock', () => {
    expect(
      shouldAutoPeekAgentDock({
        ...base,
        layoutMode: 'operator',
      }),
    ).toBe(false);
    expect(
      shouldAutoPeekAgentDock({
        ...base,
        agentDockCollapsed: false,
      }),
    ).toBe(false);
  });

  it('ignores zero approvals', () => {
    expect(
      shouldAutoPeekAgentDock({
        ...base,
        pendingApprovals: 0,
      }),
    ).toBe(false);
  });
});

describe('shouldAutoPeekAgentDockForStreaming', () => {
  const base = {
    layoutMode: 'ide' as const,
    agentDockCollapsed: true,
    streaming: true,
    streamMessageId: 'msg_abc',
    alreadyPeekedStreamMessageIds: new Set<string>(),
  };

  it('never auto-peeks for streaming — quiet IDE keeps the dock collapsed', () => {
    expect(shouldAutoPeekAgentDockForStreaming(base)).toBe(false);
    expect(
      shouldAutoPeekAgentDockForStreaming({
        ...base,
        streamMessageId: 'msg_def',
      }),
    ).toBe(false);
  });
});

describe('shouldAutoPeekAgentDockForRun', () => {
  const base = {
    layoutMode: 'ide' as const,
    agentDockCollapsed: true,
    runPhase: 'executing',
    runId: 'run_abc',
    alreadyPeekedRunIds: new Set<string>(),
  };

  it('never auto-peeks for run phase — AGENT chip pulses instead', () => {
    expect(shouldAutoPeekAgentDockForRun(base)).toBe(false);
    expect(
      shouldAutoPeekAgentDockForRun({
        ...base,
        runPhase: 'review_ready',
      }),
    ).toBe(false);
  });
});

describe('shouldAutoPeekAgentDockForEmployeeFailure', () => {
  const base = {
    layoutMode: 'ide' as const,
    agentDockCollapsed: true,
    employeeFailureLine: 'Last job failed: vitest assertion failed',
    employeeFailurePeekKey: 'e1:run_abc',
    agentStreamActive: false,
    alreadyPeekedFailureKeys: new Set<string>(),
  };

  it('opens the dock once per failed job in IDE mode', () => {
    expect(shouldAutoPeekAgentDockForEmployeeFailure(base)).toBe(true);
    expect(
      shouldAutoPeekAgentDockForEmployeeFailure({
        ...base,
        alreadyPeekedFailureKeys: new Set(['e1:run_abc']),
      }),
    ).toBe(false);
    expect(
      shouldAutoPeekAgentDockForEmployeeFailure({
        ...base,
        employeeFailurePeekKey: 'e1:run_def',
      }),
    ).toBe(true);
  });

  it('waits until the agent stream finishes before peeking', () => {
    expect(
      shouldAutoPeekAgentDockForEmployeeFailure({
        ...base,
        agentStreamActive: true,
      }),
    ).toBe(false);
  });

  it('ignores operator layout, expanded dock, and missing failure state', () => {
    expect(
      shouldAutoPeekAgentDockForEmployeeFailure({
        ...base,
        layoutMode: 'operator',
      }),
    ).toBe(false);
    expect(
      shouldAutoPeekAgentDockForEmployeeFailure({
        ...base,
        agentDockCollapsed: false,
      }),
    ).toBe(false);
    expect(
      shouldAutoPeekAgentDockForEmployeeFailure({
        ...base,
        employeeFailureLine: null,
      }),
    ).toBe(false);
    expect(
      shouldAutoPeekAgentDockForEmployeeFailure({
        ...base,
        employeeFailurePeekKey: null,
      }),
    ).toBe(false);
  });
});
