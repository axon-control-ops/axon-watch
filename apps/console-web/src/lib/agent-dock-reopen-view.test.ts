import { describe, expect, it } from 'vitest';

import {
  agentDockActivityBarAriaLabel,
  agentDockActivityBarTitle,
  agentDockCollapseTitle,
  agentDockReopenAlive,
  agentDockReopenAriaLabel,
  agentDockReopenEmployeeFailure,
  agentDockReopenEmployeeInterrupted,
  agentDockReopenTitle,
} from './agent-dock-reopen-view';

const idle = { streaming: false, pendingApprovals: 0, runPhase: null };

describe('agent dock reopen view', () => {
  it('names the expanded dock collapse control with the shortcut', () => {
    expect(agentDockCollapseTitle()).toBe('Collapse agent dock (Ctrl/Cmd+\\)');
  });

  it('names the collapsed strip with the expand shortcut by default', () => {
    expect(agentDockReopenTitle(idle)).toBe('Expand agent dock (Ctrl/Cmd+\\)');
    expect(agentDockReopenAriaLabel(idle)).toBe('Expand agent dock');
  });

  it('surfaces live agent activity while the dock is collapsed', () => {
    expect(agentDockReopenTitle({ ...idle, streaming: true })).toBe(
      'Expand agent dock (Ctrl/Cmd+\\) · Agent is responding',
    );
    expect(agentDockReopenAriaLabel({ ...idle, streaming: true })).toBe(
      'Expand agent dock, agent is responding',
    );
  });

  it('surfaces pending approvals while the dock is collapsed', () => {
    expect(agentDockReopenTitle({ ...idle, pendingApprovals: 1 })).toBe(
      'Expand agent dock (Ctrl/Cmd+\\) · 1 approval waiting',
    );
    expect(
      agentDockReopenTitle({ streaming: true, pendingApprovals: 2, runPhase: null }),
    ).toBe('Expand agent dock (Ctrl/Cmd+\\) · Agent is responding · 2 approvals waiting');
    expect(
      agentDockReopenAriaLabel({ streaming: true, pendingApprovals: 2, runPhase: null }),
    ).toBe('Expand agent dock, agent is responding, 2 approvals waiting');
  });

  it('surfaces active run phases when streaming and approvals are idle', () => {
    expect(agentDockReopenTitle({ ...idle, runPhase: 'executing' })).toContain('Run in progress');
    expect(agentDockReopenTitle({ ...idle, runPhase: 'review_ready' })).toContain('Review ready');
    expect(agentDockReopenAriaLabel({ ...idle, runPhase: 'executing' })).toContain(
      'run in progress',
    );
  });

  it('treats executing and review-ready runs as live attention', () => {
    expect(agentDockReopenAlive({ ...idle, runPhase: 'executing' })).toBe(true);
    expect(agentDockReopenAlive({ ...idle, runPhase: 'review_ready' })).toBe(true);
    expect(agentDockReopenAlive({ ...idle, runPhase: 'paused' })).toBe(false);
  });

  it('surfaces speaking while the dock is collapsed', () => {
    expect(agentDockReopenTitle({ ...idle, speaking: true })).toBe(
      'Expand agent dock (Ctrl/Cmd+\\) · Speaking',
    );
    expect(agentDockReopenAriaLabel({ ...idle, speaking: true })).toBe(
      'Expand agent dock, speaking',
    );
    expect(agentDockReopenAlive({ ...idle, speaking: true })).toBe(true);
  });

  it('surfaces failed teammate shifts while the dock is collapsed', () => {
    expect(
      agentDockReopenTitle({
        ...idle,
        employeeFailureLine: 'Last shift failed: timeout',
      }),
    ).toBe('Expand agent dock (Ctrl/Cmd+\\) · Last shift failed');
    expect(
      agentDockReopenAriaLabel({
        ...idle,
        employeeFailureLine: 'Last shift failed: timeout',
      }),
    ).toBe('Expand agent dock, last shift failed');
    expect(
      agentDockReopenAlive({
        ...idle,
        employeeFailureLine: 'Last shift failed: timeout',
      }),
    ).toBe(true);
    expect(
      agentDockReopenEmployeeFailure({
        ...idle,
        employeeFailureLine: 'Last shift failed: timeout',
      }),
    ).toBe(true);
    expect(
      agentDockReopenEmployeeInterrupted({
        ...idle,
        employeeFailureLine: 'Last shift failed: timeout',
      }),
    ).toBe(false);
  });

  it('surfaces interrupted teammate shifts with amber copy while the dock is collapsed', () => {
    const interrupted = {
      ...idle,
      employeeFailureLine:
        'Last shift interrupted before it could finish — use Continue shift to pick up where you left off.',
      employeeShiftInterrupted: true,
    };
    expect(agentDockReopenTitle(interrupted)).toBe(
      'Expand agent dock (Ctrl/Cmd+\\) · Shift interrupted',
    );
    expect(agentDockReopenAriaLabel(interrupted)).toBe(
      'Expand agent dock, shift interrupted',
    );
    expect(agentDockReopenEmployeeFailure(interrupted)).toBe(false);
    expect(agentDockReopenEmployeeInterrupted(interrupted)).toBe(true);
    expect(
      agentDockActivityBarTitle(interrupted, false),
    ).toBe('Agent dock (Ctrl/Cmd+\\) · Shift interrupted');
  });

  it('defers failure chrome while streaming, approvals, or active runs take priority', () => {
    const failed = { ...idle, employeeFailureLine: 'Last shift failed: timeout' };
    expect(agentDockReopenEmployeeFailure({ ...failed, streaming: true })).toBe(false);
    expect(agentDockReopenEmployeeFailure({ ...failed, pendingApprovals: 1 })).toBe(false);
    expect(agentDockReopenEmployeeFailure({ ...failed, runPhase: 'executing' })).toBe(false);
    expect(agentDockReopenEmployeeFailure({ ...failed, runPhase: 'review_ready' })).toBe(false);
    expect(agentDockReopenAlive({ ...failed, streaming: true })).toBe(true);
  });

  it('names the activity-bar agent button with expand or collapse intent', () => {
    expect(agentDockActivityBarTitle(idle, false)).toBe('Agent dock (Ctrl/Cmd+\\)');
    expect(agentDockActivityBarTitle(idle, true)).toBe(
      'Agent dock (Ctrl/Cmd+\\) · Click to collapse',
    );
    expect(agentDockActivityBarAriaLabel(idle, false)).toBe('Expand agent dock');
    expect(agentDockActivityBarAriaLabel(idle, true)).toBe('Collapse agent dock');
  });

  it('surfaces live agent activity on the activity-bar agent button', () => {
    expect(
      agentDockActivityBarTitle({ streaming: true, pendingApprovals: 1, runPhase: null }, false),
    ).toBe('Agent dock (Ctrl/Cmd+\\) · Agent is responding · 1 approval waiting');
    expect(
      agentDockActivityBarAriaLabel(
        { streaming: true, pendingApprovals: 1, runPhase: null },
        true,
      ),
    ).toBe('Collapse agent dock, agent is responding, 1 approval waiting');
  });
});
