import { describe, expect, it, vi } from 'vitest';

import {
  maybeSpeakOperatorAlert,
  shouldSpeakAlert,
  shouldUseMobileCompactLayout,
  spokenAlertDedupeKey,
} from './operator-presence';

describe('operator presence helpers', () => {
  it('prefers compact layout when viewport flag is set', () => {
    expect(
      shouldUseMobileCompactLayout(1200, {
        persona_voice_line: 'KAIRO: ready',
        presence_state: 'observing',
        settings: {
          operator_persona_enabled: true,
          spoken_alerts_enabled: true,
          privacy_mode: false,
          mobile_compact_preferred: true,
          kairo_narration: 'conversational',
          ide_voice_strip_enabled: false,
        },
        spoken_alert: {
          eligible: false,
          reason: 'no_interruptive_signal',
          signal_id: null,
          message: '',
        },
        mobile: { compact_layout: true, foreground_only: true },
      }),
    ).toBe(true);
  });

  it('dedupes spoken alerts within a session', () => {
    const storage = {
      getItem: vi.fn().mockReturnValue(null),
      setItem: vi.fn(),
    };
    const alert = {
      eligible: true,
      reason: 'operator_approval_required',
      signal_id: null,
      message: 'KAIRO: 1 approval waiting for your review.',
    };

    expect(shouldSpeakAlert(alert, storage)).toBe(true);
    storage.getItem.mockReturnValue(spokenAlertDedupeKey(alert));
    expect(shouldSpeakAlert(alert, storage)).toBe(false);
  });

  it('speaks eligible alerts once', () => {
    const storage = {
      getItem: vi.fn().mockReturnValue(null),
      setItem: vi.fn(),
    };
    const speech = { speak: vi.fn(), getVoices: vi.fn().mockReturnValue([]) };
    const spoken = maybeSpeakOperatorAlert(
      {
        eligible: true,
        reason: 'high_urgency_signal',
        signal_id: 'signal_x',
        message: 'KAIRO attention: Console web connector unavailable.',
      },
      speech,
      storage,
    );
    expect(spoken).toBe(true);
    expect(storage.setItem).toHaveBeenCalled();
  });
});
