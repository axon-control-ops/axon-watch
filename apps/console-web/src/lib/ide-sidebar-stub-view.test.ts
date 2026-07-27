import { describe, expect, it } from 'vitest';

import {
  buildIdeAgentSidebarStub,
  buildIdeRunPanelConnectorNotice,
  buildIdeTerminalSidebarStub,
  ideSidebarStubActionAriaLabel,
  ideSidebarStubUsesLiveRegion,
} from './ide-sidebar-stub-view';

describe('buildIdeAgentSidebarStub', () => {
  it('surfaces approval attention when the dock is collapsed', () => {
    const panel = buildIdeAgentSidebarStub({
      agentDockCollapsed: true,
      streaming: false,
      pendingApprovals: 2,
      runPhase: null,
    });

    expect(panel.tone).toBe('attention');
    expect(panel.lines[0]).toContain('2 approvals waiting');
    expect(panel.actionLabel).toBe('Expand agent dock');
  });

  it('surfaces streaming guidance when the agent is responding', () => {
    const panel = buildIdeAgentSidebarStub({
      agentDockCollapsed: true,
      streaming: true,
      pendingApprovals: 0,
      runPhase: 'executing',
    });

    expect(panel.tone).toBe('streaming');
    expect(panel.lines[0]).toContain('responding');
  });

  it('offers collapse when the dock is already open', () => {
    const panel = buildIdeAgentSidebarStub({
      agentDockCollapsed: false,
      streaming: true,
      pendingApprovals: 1,
      runPhase: null,
    });

    expect(panel.actionLabel).toBe('Collapse agent dock');
  });

  it('surfaces run phase guidance when the dock stays collapsed', () => {
    const executing = buildIdeAgentSidebarStub({
      agentDockCollapsed: true,
      streaming: false,
      pendingApprovals: 0,
      runPhase: 'executing',
    });
    const reviewReady = buildIdeAgentSidebarStub({
      agentDockCollapsed: true,
      streaming: false,
      pendingApprovals: 0,
      runPhase: 'review_ready',
    });

    expect(executing.lines[0]).toContain('Run in progress');
    expect(reviewReady.lines[0]).toContain('Review ready');
  });

  it('surfaces failed teammate shift guidance when the dock is collapsed', () => {
    const failureLine = 'Last job failed: vitest assertion failed';
    const panel = buildIdeAgentSidebarStub({
      agentDockCollapsed: true,
      streaming: false,
      pendingApprovals: 0,
      runPhase: null,
      employeeFailureLine: failureLine,
      employeeRetryActionLabel: 'Try again',
    });

    expect(panel.tone).toBe('failure');
    expect(panel.lines[0]).toBe(failureLine);
    expect(panel.lines.join(' ')).toContain('Try again');
    expect(panel.actionLabel).toBe('Expand agent dock');
    expect(panel.secondaryActionLabel).toBe('Try again');
  });

  it('surfaces interrupted teammate shift guidance when the dock is collapsed', () => {
    const panel = buildIdeAgentSidebarStub({
      agentDockCollapsed: true,
      streaming: false,
      pendingApprovals: 0,
      runPhase: null,
      employeeFailureLine:
        'Last job was interrupted before it could finish — tap Continue to pick up where they left off.',
      employeeShiftInterrupted: true,
      employeeRetryActionLabel: 'Continue',
    });

    expect(panel.tone).toBe('interrupted');
    expect(panel.lines.join(' ')).toContain('Continue');
    expect(panel.lines.join(' ')).not.toContain('Try again in the failure banner');
    expect(panel.secondaryActionLabel).toBe('Continue');
  });

  it('keeps failure guidance below approvals and streaming', () => {
    expect(
      buildIdeAgentSidebarStub({
        agentDockCollapsed: true,
        streaming: false,
        pendingApprovals: 1,
        runPhase: null,
        employeeFailureLine: 'Last job failed: timeout',
      }).lines[0],
    ).toContain('approval');
    expect(
      buildIdeAgentSidebarStub({
        agentDockCollapsed: true,
        streaming: true,
        pendingApprovals: 0,
        runPhase: null,
        employeeFailureLine: 'Last job failed: timeout',
      }).lines[0],
    ).toContain('responding');
  });
});

describe('buildIdeRunPanelConnectorNotice', () => {
  it('surfaces watch offline guidance before stale connector counts', () => {
    const notice = buildIdeRunPanelConnectorNotice({
      watchConnected: false,
      requiredConnectorsUnavailable: 2,
      legacyConnectorGlanceVisible: true,
    });

    expect(notice?.tone).toBe('attention');
    expect(notice?.lines[0]).toContain('Watch offline');
    expect(notice?.actionLabel).toBe('Open connectors');
  });

  it('surfaces required connector attention in the Run panel', () => {
    const notice = buildIdeRunPanelConnectorNotice({
      watchConnected: true,
      requiredConnectorsUnavailable: 2,
      legacyConnectorGlanceVisible: false,
    });

    expect(notice?.tone).toBe('attention');
    expect(notice?.lines[0]).toContain('2 required connectors down');
    expect(notice?.actionLabel).toBe('Open connectors');
  });

  it('surfaces legacy connector guidance when optional Axon Local is offline', () => {
    const notice = buildIdeRunPanelConnectorNotice({
      watchConnected: true,
      requiredConnectorsUnavailable: 0,
      legacyConnectorGlanceVisible: true,
    });

    expect(notice?.tone).toBe('neutral');
    expect(notice?.lines[0]).toContain('Legacy Axon Local');
    expect(notice?.actionLabel).toBe('Open connectors');
  });

  it('returns null when connectors are healthy', () => {
    expect(
      buildIdeRunPanelConnectorNotice({
        watchConnected: true,
        requiredConnectorsUnavailable: 0,
        legacyConnectorGlanceVisible: false,
      }),
    ).toBeNull();
  });
});

describe('ideSidebarStubUsesLiveRegion', () => {
  it('announces agent attention, failure, interrupted, and streaming states', () => {
    expect(ideSidebarStubUsesLiveRegion('neutral', 'agent')).toBe(false);
    expect(ideSidebarStubUsesLiveRegion('attention', 'agent')).toBe(true);
    expect(ideSidebarStubUsesLiveRegion('failure', 'agent')).toBe(true);
    expect(ideSidebarStubUsesLiveRegion('interrupted', 'agent')).toBe(true);
    expect(ideSidebarStubUsesLiveRegion('streaming', 'agent')).toBe(true);
  });

  it('announces terminal attention only when a run needs shell output', () => {
    expect(ideSidebarStubUsesLiveRegion('neutral', 'terminal')).toBe(false);
    expect(ideSidebarStubUsesLiveRegion('attention', 'terminal')).toBe(true);
  });
});

describe('ideSidebarStubActionAriaLabel', () => {
  it('expands agent and terminal stub button labels for screen readers', () => {
    expect(ideSidebarStubActionAriaLabel('Expand agent dock', 'agent')).toContain('right edge');
    expect(ideSidebarStubActionAriaLabel('Show terminal', 'terminal')).toContain('below the editor');
    expect(ideSidebarStubActionAriaLabel('Try again', 'agent')).toContain('agent dock composer');
    expect(ideSidebarStubActionAriaLabel('Continue', 'agent')).toContain('agent dock composer');
    expect(ideSidebarStubActionAriaLabel('Custom action', 'agent')).toBe('Custom action');
  });
});

describe('buildIdeTerminalSidebarStub', () => {
  it('prompts to show the terminal when it is hidden', () => {
    const panel = buildIdeTerminalSidebarStub({ terminalVisible: false, runPhase: null });

    expect(panel.actionLabel).toBe('Show terminal');
    expect(panel.lines.join(' ')).toContain('Ctrl/Cmd+J');
  });

  it('mentions active run phases when the terminal is hidden', () => {
    expect(
      buildIdeTerminalSidebarStub({ terminalVisible: false, runPhase: 'executing' }).lines[0],
    ).toContain('Run in progress');
    expect(
      buildIdeTerminalSidebarStub({ terminalVisible: false, runPhase: 'review_ready' }).lines[0],
    ).toContain('Review ready');
  });

  it('offers hide when the terminal is visible', () => {
    const panel = buildIdeTerminalSidebarStub({ terminalVisible: true, runPhase: null });

    expect(panel.actionLabel).toBe('Hide terminal');
  });

  it('uses attention tone when an active run needs shell output', () => {
    expect(
      buildIdeTerminalSidebarStub({ terminalVisible: false, runPhase: 'executing' }).tone,
    ).toBe('attention');
    expect(
      buildIdeTerminalSidebarStub({ terminalVisible: false, runPhase: 'review_ready' }).tone,
    ).toBe('attention');
    expect(buildIdeTerminalSidebarStub({ terminalVisible: false, runPhase: null }).tone).toBe(
      'neutral',
    );
  });
});
