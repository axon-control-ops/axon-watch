import { describe, expect, it } from 'vitest';

import {
  shouldShowVaxonRosterVoiceDock,
  vaxonRosterDisplayLine,
} from './use-vaxon-roster-voice-dock';

describe('shouldShowVaxonRosterVoiceDock', () => {
  it('always renders the canonical VAXON name', () => {
    expect(vaxonRosterDisplayLine('Vekson is attending the signal.')).toBe(
      'VAXON is attending the signal.',
    );
  });

  it('hides the roster popup on Mission Control because the VAXON tab owns presence', () => {
    expect(
      shouldShowVaxonRosterVoiceDock({
        layoutMode: 'operator',
        operatorBrainGalaxyActive: false,
        operatorCenterView: 'mission',
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
