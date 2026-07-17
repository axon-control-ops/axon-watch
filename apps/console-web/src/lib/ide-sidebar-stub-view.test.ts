import { describe, expect, it } from 'vitest';

import {
  buildIdeAgentSidebarStub,
  buildIdeRunPanelConnectorNotice,
  buildIdeTerminalSidebarStub,
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
});

describe('buildIdeRunPanelConnectorNotice', () => {
  it('surfaces required connector attention in the Run panel', () => {
    const notice = buildIdeRunPanelConnectorNotice({
      requiredConnectorsUnavailable: 2,
      legacyConnectorGlanceVisible: false,
    });

    expect(notice?.tone).toBe('attention');
    expect(notice?.lines[0]).toContain('2 required connectors down');
    expect(notice?.actionLabel).toBe('Open connectors');
  });

  it('surfaces legacy connector guidance when optional Axon Local is offline', () => {
    const notice = buildIdeRunPanelConnectorNotice({
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
        requiredConnectorsUnavailable: 0,
        legacyConnectorGlanceVisible: false,
      }),
    ).toBeNull();
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
