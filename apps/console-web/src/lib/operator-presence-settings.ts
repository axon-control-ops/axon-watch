import type { OperatorPresenceSettings } from '../contracts/canonical';

export const OPERATOR_PRESENCE_SETTINGS_KEY = 'axon-x:operator-presence-settings';

/** axon-local desktop voice deck defaults. */
export const DEFAULT_SPEECH_RATE = 1.0;
export const DEFAULT_SPEECH_PITCH = 1.04;

export function defaultOperatorPresenceSettings(): OperatorPresenceSettings {
  return {
    operator_persona_enabled: true,
    spoken_alerts_enabled: true,
    privacy_mode: false,
    mobile_compact_preferred: true,
    kairo_narration: 'conversational',
    ide_voice_strip_enabled: false,
    hands_free_enabled: false,
    speech_rate: DEFAULT_SPEECH_RATE,
    speech_pitch: DEFAULT_SPEECH_PITCH,
  };
}

function normalizeSpeechRate(raw: unknown): number {
  const value = typeof raw === 'number' ? raw : Number.parseFloat(String(raw ?? ''));
  if (!Number.isFinite(value)) {
    return DEFAULT_SPEECH_RATE;
  }
  return Math.round(Math.max(0.5, Math.min(1.3, value)) * 100) / 100;
}

function normalizeSpeechPitch(raw: unknown): number {
  const value = typeof raw === 'number' ? raw : Number.parseFloat(String(raw ?? ''));
  if (!Number.isFinite(value)) {
    return DEFAULT_SPEECH_PITCH;
  }
  return Math.round(Math.max(0.5, Math.min(1.5, value)) * 100) / 100;
}

export function normalizeOperatorPresenceSettings(
  raw: Partial<OperatorPresenceSettings> | null | undefined,
): OperatorPresenceSettings {
  const defaults = defaultOperatorPresenceSettings();
  if (!raw) {
    return defaults;
  }
  return {
    operator_persona_enabled: raw.operator_persona_enabled ?? defaults.operator_persona_enabled,
    spoken_alerts_enabled: raw.spoken_alerts_enabled ?? defaults.spoken_alerts_enabled,
    privacy_mode: raw.privacy_mode ?? defaults.privacy_mode,
    mobile_compact_preferred: raw.mobile_compact_preferred ?? defaults.mobile_compact_preferred,
    kairo_narration:
      raw.kairo_narration === 'off' ||
      raw.kairo_narration === 'minimal' ||
      raw.kairo_narration === 'conversational'
        ? raw.kairo_narration
        : defaults.kairo_narration,
    ide_voice_strip_enabled: raw.ide_voice_strip_enabled ?? defaults.ide_voice_strip_enabled,
    hands_free_enabled: raw.hands_free_enabled ?? defaults.hands_free_enabled,
    speech_rate: normalizeSpeechRate(raw.speech_rate ?? defaults.speech_rate),
    speech_pitch: normalizeSpeechPitch(raw.speech_pitch ?? defaults.speech_pitch),
  };
}

export function readPersistedOperatorPresenceSettings(
  storage: Pick<Storage, 'getItem'> = localStorage,
): OperatorPresenceSettings | null {
  const raw = storage.getItem(OPERATOR_PRESENCE_SETTINGS_KEY);
  if (!raw) {
    return null;
  }
  try {
    return normalizeOperatorPresenceSettings(JSON.parse(raw) as Partial<OperatorPresenceSettings>);
  } catch {
    return null;
  }
}

export function persistOperatorPresenceSettings(
  settings: OperatorPresenceSettings,
  storage: Pick<Storage, 'setItem'> = localStorage,
): void {
  storage.setItem(OPERATOR_PRESENCE_SETTINGS_KEY, JSON.stringify(settings));
}

/** Format like axon-local mono readout (`1.00`). */
export function formatVoiceTuningValue(value: number): string {
  return value.toFixed(2);
}
