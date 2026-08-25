import { describe, expect, it } from 'vitest';

import { buildIdeQuickGuide } from './ide-quick-guide';
import { buildConnectorIdeQuickGuide } from './ide-quick-guide-connectors';

describe('buildConnectorIdeQuickGuide', () => {
  const base = {
    idleRun: true,
    terminalVisible: false,
    watchConnected: true,
    requiredConnectorsUnavailable: 0,
    legacyConnectorGlanceVisible: false,
  };

  it('surfaces watch offline guidance instead of stale connector counts', () => {
    const guide = buildConnectorIdeQuickGuide({
      ...base,
      watchConnected: false,
      requiredConnectorsUnavailable: 2,
      legacyConnectorGlanceVisible: true,
    });

    expect(guide?.tone).toBe('attention');
    expect(guide?.title).toContain('Watch offline');
    expect(guide?.steps.join(' ')).toContain('connector probes paused');
    expect(guide?.actions.map((action) => action.id)).toEqual([
      'open-connectors',
      'show-terminal',
    ]);
  });

  it('prioritizes required connector guidance when idle and probes are down', () => {
    const guide = buildConnectorIdeQuickGuide({
      ...base,
      requiredConnectorsUnavailable: 2,
    });

    expect(guide?.tone).toBe('attention');
    expect(guide?.title).toContain('2 required connectors down');
    expect(guide?.steps.join(' ')).toContain('Reprobe');
    expect(guide?.actions.map((action) => action.id)).toEqual([
      'open-connectors',
      'show-terminal',
    ]);
  });

  it('surfaces optional connector guidance when a non-required connector is offline', () => {
    const guide = buildConnectorIdeQuickGuide({
      ...base,
      terminalVisible: true,
      legacyConnectorGlanceVisible: true,
    });

    expect(guide?.title).toContain('Optional connector');
    expect(guide?.steps.join(' ')).toContain('Optional connector only');
    expect(guide?.actions).toEqual([{ id: 'open-connectors', label: 'Open connectors' }]);
  });

  it('returns null when a run is active', () => {
    expect(buildConnectorIdeQuickGuide({ ...base, idleRun: false })).toBeNull();
  });
});

describe('buildIdeQuickGuide connector integration', () => {
  const base = {
    layoutMode: 'ide' as const,
    agentDockCollapsed: true,
    terminalVisible: false,
    pendingApprovals: 0,
    streaming: false,
    runPhase: null,
  };

  it('does not override run guidance when a run is active', () => {
    const guide = buildIdeQuickGuide({
      ...base,
      runPhase: 'executing',
      requiredConnectorsUnavailable: 1,
    });

    expect(guide?.title).toContain('Run in progress');
    expect(guide?.actions.map((action) => action.id)).toEqual([
      'expand-agent-dock',
      'show-terminal',
    ]);
  });
});
