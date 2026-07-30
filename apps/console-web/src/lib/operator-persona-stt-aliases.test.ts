import { describe, expect, it } from 'vitest';

import { OPERATOR_PERSONA_NAME } from './operator-persona-name';
import {
  normalizePersonaSttAliases,
  personaWakeMatchScore,
  pickBestSpeechTranscript,
} from './operator-persona-stt-aliases';

describe('operator persona STT aliases', () => {
  it.each([
    ['vixen', 'check health'],
    ['vicksen', 'check health'],
    ['vikson', 'check health'],
    ['vicson', 'check health'],
    ['vickson', 'check health'],
    ['vixson', 'check health'],
    ['vicsen', 'check health'],
    ['vicen', 'check health'],
    ['wixen', 'check health'],
    ['wax on', 'check health'],
    ['vax on', 'check health'],
    ['backs on', 'check health'],
    ['back son', 'check health'],
    ['cairo', 'check health'],
    ['axon vixen', 'check health'],
    ['V.A.X.O.N', 'check health'],
    ['Vekson', 'check health'],
  ])('maps %s mishear to VAXON', (phrase, command) => {
    const normalized = normalizePersonaSttAliases(`hey ${phrase} ${command}`);
    expect(normalized.toLowerCase()).toContain(OPERATOR_PERSONA_NAME.toLowerCase());
  });

  it.each(['vaccine', 'ericsson', 'eric son', 'erickson'])(
    'maps operator-reported mishear %s to VAXON',
    (phrase) => {
      const normalized = normalizePersonaSttAliases(`${phrase} what signals need attention`);
      expect(normalized.toLowerCase()).toContain(OPERATOR_PERSONA_NAME.toLowerCase());
    },
  );

  it('does not rewrite unrelated words', () => {
    expect(normalizePersonaSttAliases('vision check health')).toBe('vision check health');
    expect(normalizePersonaSttAliases('vector status')).toBe('vector status');
    expect(normalizePersonaSttAliases('check action items')).toBe('check action items');
  });

  it('prefers wake-word alternative transcripts', () => {
    expect(
      pickBestSpeechTranscript([
        'hey vision check health',
        'hey vicksen check health',
      ]),
    ).toBe('hey vicksen check health');
    expect(personaWakeMatchScore('hey vixen check health')).toBeGreaterThanOrEqual(50);
  });
});
