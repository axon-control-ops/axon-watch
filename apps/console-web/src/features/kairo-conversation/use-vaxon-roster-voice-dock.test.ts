import { describe, expect, it } from 'vitest';

import { shouldShowVaxonRosterVoiceDock } from './use-vaxon-roster-voice-dock';

describe('shouldShowVaxonRosterVoiceDock', () => {
  it('hides the roster popup on Mission Control because right Live Ops owns VAXON', () => {
    expect(
      shouldShowVaxonRosterVoiceDock({
        layoutMode: 'operator',
        operatorBrainGalaxyActive: false,
        operatorCenterView: 'grid',
        voiceDockVisible: true,
      }),
    ).toBe(false);
  });

  it('also avoids duplicating the IDE VAXON presence', () => {
    expect(
      shouldShowVaxonRosterVoiceDock({
        layoutMode: 'ide',
        operatorBrainGalaxyActive: false,
        voiceDockVisible: true,
      }),
    ).toBe(false);
  });

  it('keeps the roster interaction available on Brain Graph', () => {
    expect(
      shouldShowVaxonRosterVoiceDock({
        layoutMode: 'operator',
        operatorBrainGalaxyActive: true,
        operatorCenterView: 'graph',
        voiceDockVisible: true,
      }),
    ).toBe(true);
  });
});
