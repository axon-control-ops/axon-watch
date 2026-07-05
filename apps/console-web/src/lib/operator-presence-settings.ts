import type { OperatorPresenceSettings } from '../contracts/canonical';

export const OPERATOR_PRESENCE_SETTINGS_KEY = 'axon-x:operator-presence-settings';

export function defaultOperatorPresenceSettings(): OperatorPresenceSettings {
  return {
    operator_persona_enabled: true,
    spoken_alerts_enabled: true,
    privacy_mode: false,
    mobile_compact_preferred: true,
  };
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
