import { describe, expect, it } from 'vitest';

import {
  buildGalaxyAmbientPanels,
  galaxyAmbientSpokenLine,
  selectVisibleAmbientPanels,
} from './galaxy-ambient-hud-view';

const base = {
  nowMs: 0,
  presencePhase: 'idle',
  workspaceLabel: 'DashPro',
  criticalSignals: 0,
  highSignals: 0,
  runPhaseLabel: null,
  topSignalTitle: null,
  specialtyRouteLine: null,
  watchConnected: true,
};

describe('galaxy ambient HUD', () => {
  it('always includes core presence + watch + scan panels', () => {
    const panels = buildGalaxyAmbientPanels(base);
    expect(panels.map((panel) => panel.id)).toEqual(
      expect.arrayContaining(['presence', 'watch', 'scan']),
    );
  });

  it('rotates visible windows over time', () => {
    const panels = buildGalaxyAmbientPanels({
      ...base,
      criticalSignals: 1,
      topSignalTitle: 'DashPro Sentry critical',
      runPhaseLabel: 'REVIEW READY',
    });
    const first = selectVisibleAmbientPanels(panels, 0, 1000, 2).map((panel) => panel.id);
    const second = selectVisibleAmbientPanels(panels, 1000, 1000, 2).map((panel) => panel.id);
    expect(first).not.toEqual(second);
  });

  it('speaks critical signal context when present', () => {
    expect(
      galaxyAmbientSpokenLine({
        ...base,
        criticalSignals: 1,
        topSignalTitle: 'DashPro Sentry critical',
      }),
    ).toContain('DashPro Sentry critical');
  });
});
