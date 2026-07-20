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

  it('opens the dock once per stream message in IDE mode', () => {
    expect(shouldAutoPeekAgentDockForStreaming(base)).toBe(true);
    expect(
      shouldAutoPeekAgentDockForStreaming({
        ...base,
        alreadyPeekedStreamMessageIds: new Set(['msg_abc']),
      }),
    ).toBe(false);
    expect(
      shouldAutoPeekAgentDockForStreaming({
        ...base,
        streamMessageId: 'msg_def',
      }),
    ).toBe(true);
  });

  it('does not peek when the dock is open or the agent is idle', () => {
    expect(
      shouldAutoPeekAgentDockForStreaming({
        ...base,
        agentDockCollapsed: false,
      }),
    ).toBe(false);
    expect(
      shouldAutoPeekAgentDockForStreaming({
        ...base,
        streaming: false,
      }),
    ).toBe(false);
    expect(
      shouldAutoPeekAgentDockForStreaming({
        ...base,
        streamMessageId: null,
      }),
    ).toBe(false);
  });

  it('ignores operator layout', () => {
    expect(
      shouldAutoPeekAgentDockForStreaming({
        ...base,
        layoutMode: 'operator',
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

  it('opens the dock once per active run in IDE mode', () => {
    expect(shouldAutoPeekAgentDockForRun(base)).toBe(true);
    expect(
      shouldAutoPeekAgentDockForRun({
        ...base,
        alreadyPeekedRunIds: new Set(['run_abc']),
      }),
    ).toBe(false);
    expect(
      shouldAutoPeekAgentDockForRun({
        ...base,
        runId: 'run_def',
      }),
    ).toBe(true);
  });

  it('peeks for review_ready as well as executing', () => {
    expect(
      shouldAutoPeekAgentDockForRun({
        ...base,
        runPhase: 'review_ready',
      }),
    ).toBe(true);
  });

  it('ignores idle phases, operator layout, and expanded dock', () => {
    expect(
      shouldAutoPeekAgentDockForRun({
        ...base,
        runPhase: 'paused',
      }),
    ).toBe(false);
    expect(
      shouldAutoPeekAgentDockForRun({
        ...base,
        layoutMode: 'operator',
      }),
    ).toBe(false);
    expect(
      shouldAutoPeekAgentDockForRun({
        ...base,
        agentDockCollapsed: false,
      }),
    ).toBe(false);
    expect(
      shouldAutoPeekAgentDockForRun({
        ...base,
        runId: null,
      }),
    ).toBe(false);
  });
});

describe('shouldAutoPeekAgentDockForEmployeeFailure', () => {
  const base = {
    layoutMode: 'ide' as const,
    agentDockCollapsed: true,
    employeeFailureLine: 'Last shift failed: vitest assertion failed',
    employeeFailurePeekKey: 'e1:run_abc',
    agentStreamActive: false,
    alreadyPeekedFailureKeys: new Set<string>(),
  };

  it('opens the dock once per failed shift in IDE mode', () => {
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
