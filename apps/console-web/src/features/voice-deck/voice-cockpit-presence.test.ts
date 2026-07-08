import { describe, expect, it } from 'vitest';

import {
  shouldReactToBriefingSpokenAlert,
  voiceCockpitStatusLine,
} from './voice-cockpit-presence';

describe('voice cockpit presence', () => {
  it('builds a status line from operator presence', () => {
    expect(
      voiceCockpitStatusLine({
        persona_voice_line: 'KAIRO: 1 approval waiting.',
        presence_state: 'alerting',
        settings: {
          operator_persona_enabled: true,
          spoken_alerts_enabled: true,
          privacy_mode: false,
          mobile_compact_preferred: true,
          kairo_narration: 'conversational',
          ide_voice_strip_enabled: false,
          hands_free_enabled: false,
        },
        spoken_alert: {
          eligible: true,
          reason: 'operator_approval_required',
          signal_id: null,
          message: 'KAIRO: 1 approval waiting.',
        },
        mobile: { compact_layout: true, foreground_only: true },
      }),
    ).toContain('approval');
  });

  it('detects eligible briefing spoken alerts', () => {
    expect(
      shouldReactToBriefingSpokenAlert({
        eligible: true,
        reason: 'operator_approval_required',
        signal_id: null,
        message: 'KAIRO attention required.',
      }),
    ).toBe(true);
    expect(
      shouldReactToBriefingSpokenAlert({
        eligible: false,
        reason: 'no_interruptive_signal',
        signal_id: null,
        message: '',
      }),
    ).toBe(false);
  });
});
