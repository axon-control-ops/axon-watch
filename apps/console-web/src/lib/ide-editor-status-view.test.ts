import { describe, expect, it } from 'vitest';

import {
  buildIdeEditorStatusAgentChip,
  buildIdeEditorStatusConnectorChip,
  buildIdeEditorStatusTerminalChip,
} from './ide-editor-status-view';

describe('buildIdeEditorStatusConnectorChip', () => {
  const base = {
    connectorsLoadState: 'loaded' as const,
    watchConnected: true,
    items: [] as const,
  };

  it('shows a compact required-down chip in the editor status bar', () => {
    expect(
      buildIdeEditorStatusConnectorChip({
        ...base,
        summary: { required_unavailable: 2 },
      }),
    ).toEqual({
      id: 'connector-required-alert',
      label: '2 REQ DOWN',
      tone: 'warning',
      title: 'Required connector down — switch to Mission Control connectors',
      ariaLabel: '2 REQ DOWN. Required connector down — switch to Mission Control connectors.',
    });
  });

  it('uses singular copy for one required connector', () => {
    expect(
      buildIdeEditorStatusConnectorChip({
        ...base,
        summary: { required_unavailable: 1 },
      })?.label,
    ).toBe('1 REQ DOWN');
  });

  it('shows a compact legacy-offline chip when optional Axon Local is down', () => {
    expect(
      buildIdeEditorStatusConnectorChip({
        ...base,
        summary: { required_unavailable: 0 },
        items: [
          {
            connector_id: 'axon_local',
            display_name: 'Axon Local',
            status: 'unavailable',
            required: false,
          },
        ],
      }),
    ).toMatchObject({
      id: 'connector-glance',
      label: 'LEGACY OFFLINE',
      tone: 'default',
    });
  });

  it('labels degraded legacy status distinctly', () => {
    expect(
      buildIdeEditorStatusConnectorChip({
        ...base,
        summary: { required_unavailable: 0 },
        items: [
          {
            connector_id: 'axon_local',
            display_name: 'Axon Local',
            status: 'degraded',
            required: false,
          },
        ],
      })?.label,
    ).toBe('LEGACY DEGRADED');
  });

  it('hides the chip when connectors are healthy', () => {
    expect(
      buildIdeEditorStatusConnectorChip({
        ...base,
        summary: { required_unavailable: 0 },
        items: [
          {
            connector_id: 'axon_local',
            display_name: 'Axon Local',
            status: 'ok',
            required: false,
          },
        ],
      }),
    ).toBeNull();
  });
});

describe('buildIdeEditorStatusTerminalChip', () => {
  it('returns null when the terminal panel is already visible', () => {
    expect(
      buildIdeEditorStatusTerminalChip({ terminalVisible: true, runPhase: 'executing' }),
    ).toBeNull();
  });

  it('surfaces run phase hints when the terminal is hidden', () => {
    const chip = buildIdeEditorStatusTerminalChip({
      terminalVisible: false,
      runPhase: 'executing',
    });

    expect(chip).toMatchObject({
      label: 'TERMINAL',
      showPulse: true,
      executing: true,
      reviewReady: false,
    });
    expect(chip?.title).toContain('Run in progress');
  });
});

describe('buildIdeEditorStatusAgentChip', () => {
  it('returns null when the agent dock is already expanded', () => {
    expect(
      buildIdeEditorStatusAgentChip({
        agentDockCollapsed: false,
        state: { streaming: true, pendingApprovals: 1, runPhase: 'executing' },
      }),
    ).toBeNull();
  });

  it('surfaces approval badge and attention styling when approvals are waiting', () => {
    const chip = buildIdeEditorStatusAgentChip({
      agentDockCollapsed: true,
      state: { streaming: false, pendingApprovals: 2, runPhase: null },
    });

    expect(chip).toMatchObject({
      label: 'AGENT',
      showBadge: 2,
      showPulse: false,
      approvals: true,
      alive: true,
    });
  });

  it('surfaces a pulse when a run needs the dock but no approvals are waiting', () => {
    const chip = buildIdeEditorStatusAgentChip({
      agentDockCollapsed: true,
      state: { streaming: false, pendingApprovals: 0, runPhase: 'review_ready' },
    });

    expect(chip).toMatchObject({
      showBadge: null,
      showPulse: true,
      reviewReady: true,
      alive: true,
    });
  });
});
