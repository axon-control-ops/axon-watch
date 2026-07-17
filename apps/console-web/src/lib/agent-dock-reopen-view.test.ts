import { describe, expect, it } from 'vitest';

import {
  agentDockActivityBarAriaLabel,
  agentDockActivityBarTitle,
  agentDockCollapseTitle,
  agentDockReopenAlive,
  agentDockReopenAriaLabel,
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
