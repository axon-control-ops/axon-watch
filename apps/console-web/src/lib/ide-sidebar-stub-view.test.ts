import { describe, expect, it } from 'vitest';

import {
  buildIdeRunPanelConnectorNotice,
  buildIdeTerminalSidebarStub,
  ideSidebarStubActionAriaLabel,
  ideSidebarStubUsesLiveRegion,
} from './ide-sidebar-stub-view';

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

  it('surfaces optional connector guidance when a non-required connector is offline', () => {
    const notice = buildIdeRunPanelConnectorNotice({
      watchConnected: true,
      requiredConnectorsUnavailable: 0,
      legacyConnectorGlanceVisible: true,
    });

    expect(notice?.tone).toBe('neutral');
    expect(notice?.lines[0]).toContain('Optional connector');
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
  it('announces terminal attention only when a run needs shell output', () => {
    expect(ideSidebarStubUsesLiveRegion('neutral', 'terminal')).toBe(false);
    expect(ideSidebarStubUsesLiveRegion('attention', 'terminal')).toBe(true);
  });
});

describe('ideSidebarStubActionAriaLabel', () => {
  it('expands agent and terminal stub button labels for screen readers', () => {
    expect(ideSidebarStubActionAriaLabel('Expand agent dock', 'agent')).toContain('right edge');
    expect(ideSidebarStubActionAriaLabel('Open Team roster', 'agent')).toContain('left sidebar');
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
