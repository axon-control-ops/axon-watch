import { describe, expect, it, vi } from 'vitest';

import {
  maybeSpeakOperatorAlert,
  shouldSpeakAlert,
  shouldUseMobileCompactLayout,
  spokenAlertDedupeKey,
} from './operator-presence';
import { defaultOperatorPresenceSettings } from './operator-presence-settings';
import { speakKairoLine } from './kairo-voice-playback';
import {
  clearQueuedSpokenAlerts,
  deliverSpokenOperatorAlert,
} from './spoken-alert-delivery';

vi.mock('./kairo-voice-playback', () => ({
  speakKairoLine: vi.fn(),
}));

vi.mock('./kairo-audio-unlock', () => ({
  isKairoMediaUnlocked: () => true,
  onKairoAudioUnlocked: () => () => undefined,
}));

describe('operator presence helpers', () => {
  it('prefers compact layout when viewport flag is set', () => {
    expect(
      shouldUseMobileCompactLayout(1200, {
        persona_voice_line: 'VAXON: ready',
        presence_state: 'observing',
        settings: {
          ...defaultOperatorPresenceSettings(),
          mobile_compact_preferred: true,
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
      message: 'VAXON: 1 approval waiting for your review.',
    };

    expect(shouldSpeakAlert(alert, storage)).toBe(true);
    storage.getItem.mockReturnValue(spokenAlertDedupeKey(alert));
    expect(shouldSpeakAlert(alert, storage)).toBe(false);
  });

  it('speaks eligible alerts once', async () => {
    clearQueuedSpokenAlerts();
    vi.mocked(speakKairoLine).mockClear();
    vi.mocked(speakKairoLine).mockResolvedValue({ engine: 'azure', reason: null });
    const storage = {
      getItem: vi.fn().mockReturnValue(null),
      setItem: vi.fn(),
    };
    const channel = await deliverSpokenOperatorAlert(
      {
        eligible: true,
        reason: 'high_urgency_signal',
        signal_id: 'signal_x',
        message: 'VAXON attention: Console web connector unavailable.',
      },
      storage,
      { queueUntilUnlock: false },
    );
    expect(channel).toBe('azure');
    expect(speakKairoLine).toHaveBeenCalledOnce();

    const spoken = await maybeSpeakOperatorAlert(
      {
        eligible: true,
        reason: 'high_urgency_signal',
        signal_id: 'signal_y',
        message: 'VAXON attention: second alert.',
      },
      storage,
    );
    expect(spoken).toBe(true);
    expect(storage.setItem).toHaveBeenCalled();
  });
});
