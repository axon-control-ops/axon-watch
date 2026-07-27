import { describe, expect, it } from 'vitest';

import { resolveIdePresencePersonaName } from './ide-presence-persona';
import { OPERATOR_PERSONA_NAME } from './operator-persona-name';

describe('resolveIdePresencePersonaName', () => {
  it('names the employee when they are the live speaker', () => {
    expect(
      resolveIdePresencePersonaName({
        speaker: { kind: 'employee', id: 'e1', name: 'Marco' },
        kairoSpeechActive: true,
        surfaceEmployeeFailure: true,
        activeEmployeeName: 'Marco',
      }),
    ).toBe('Marco');
  });

  it('keeps VAXON when VAXON is the live speaker', () => {
    expect(
      resolveIdePresencePersonaName({
        speaker: { kind: 'vaxon', id: 'vaxon', name: OPERATOR_PERSONA_NAME },
        kairoSpeechActive: true,
        surfaceEmployeeFailure: false,
        activeEmployeeName: 'Marco',
      }),
    ).toBe(OPERATOR_PERSONA_NAME);
  });

  it('falls back to the open teammate when speech is active without a speaker', () => {
    expect(
      resolveIdePresencePersonaName({
        speaker: null,
        kairoSpeechActive: true,
        surfaceEmployeeFailure: false,
        activeEmployeeName: 'Marco',
      }),
    ).toBe('Marco');
  });

  it('keeps the sticky employee name during the post-speech follow-up window', () => {
    expect(
      resolveIdePresencePersonaName({
        speaker: null,
        kairoSpeechActive: false,
        surfaceEmployeeFailure: false,
        activeEmployeeName: null,
        stickySpeakerName: 'Marco',
        stickyFollowupActive: true,
      }),
    ).toBe('Marco');
  });
});
