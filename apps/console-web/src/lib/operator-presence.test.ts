import { describe, expect, it, vi } from 'vitest';

import {
  maybeSpeakOperatorAlert,
  shouldSpeakAlert,
  shouldUseMobileCompactLayout,
  spokenAlertDedupeKey,
} from './operator-presence';
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
          operator_persona_enabled: true,
          spoken_alerts_enabled: true,
          privacy_mode: false,
          mobile_compact_preferred: true,
          kairo_narration: 'conversational',
          ide_voice_strip_enabled: false,
          hands_free_enabled: false,
          speech_rate: 1.0,
          speech_pitch: 1.04,
          azure_voice_id: 'en-GB-RyanNeural',
          stt_mode: 'browser',
          voice_routing_mode: 'template_first',
          narrate_tool_progress: false,
          proactive_duplex_enabled: false,
          autonomy_mode: 'manual',
          vaxon_model_id: 'gpt-5.4-high',
          auto_composer_runtime_override_enabled: false,
          auto_composer_runtime_target: '',
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
    const store = new Map<string, string>();
    const storage = {
      getItem: vi.fn((key: string) => store.get(key) ?? null),
      setItem: vi.fn((key: string, value: string) => {
        store.set(key, value);
      }),
    };
    const alert = {
      eligible: true,
      reason: 'operator_approval_required',
      signal_id: null,
      message: 'VAXON: 1 approval waiting for your review.',
    };

    expect(shouldSpeakAlert(alert, storage)).toBe(true);
    expect(shouldSpeakAlert(alert, storage)).toBe(false);
    expect(spokenAlertDedupeKey(alert)).toBe('operator_approval_required');
  });

  it('keeps multiple recent alert keys across tabs', () => {
    const store = new Map<string, string>();
    const storage = {
      getItem: vi.fn((key: string) => store.get(key) ?? null),
      setItem: vi.fn((key: string, value: string) => {
        store.set(key, value);
      }),
    };
    const first = {
      eligible: true,
      reason: 'autonomy_advisory',
      signal_id: 'advisory:1',
      message: 'Lead reviews are ready.',
    };
    const second = {
      eligible: true,
      reason: 'ci_remediation_failure',
      signal_id: 'signal_ci',
      message: 'CI still red.',
    };
    expect(shouldSpeakAlert(first, storage)).toBe(true);
    expect(shouldSpeakAlert(second, storage)).toBe(true);
    expect(shouldSpeakAlert(first, storage)).toBe(false);
    expect(shouldSpeakAlert(second, storage)).toBe(false);
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
