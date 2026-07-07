import { describe, expect, it } from 'vitest';

import {
  defaultOperatorPresenceSettings,
  normalizeOperatorPresenceSettings,
  OPERATOR_PRESENCE_SETTINGS_KEY,
  persistOperatorPresenceSettings,
  readPersistedOperatorPresenceSettings,
} from './operator-presence-settings';

class MemoryStorage implements Storage {
  private readonly values = new Map<string, string>();

  get length(): number {
    return this.values.size;
  }

  clear(): void {
    this.values.clear();
  }

  getItem(key: string): string | null {
    return this.values.get(key) ?? null;
  }

  key(index: number): string | null {
    return [...this.values.keys()][index] ?? null;
  }

  removeItem(key: string): void {
    this.values.delete(key);
  }

  setItem(key: string, value: string): void {
    this.values.set(key, value);
  }
}

describe('operator-presence-settings', () => {
  it('persists normalized settings to localStorage', () => {
    const storage = new MemoryStorage();
    persistOperatorPresenceSettings(
      {
        ...defaultOperatorPresenceSettings(),
        operator_persona_enabled: false,
      },
      storage,
    );

    expect(readPersistedOperatorPresenceSettings(storage)).toEqual({
      operator_persona_enabled: false,
      spoken_alerts_enabled: true,
      privacy_mode: false,
      mobile_compact_preferred: true,
      kairo_narration: 'conversational',
      ide_voice_strip_enabled: false,
    });
    expect(storage.getItem(OPERATOR_PRESENCE_SETTINGS_KEY)).toContain('"operator_persona_enabled":false');
  });

  it('merges partial payloads with defaults', () => {
    expect(normalizeOperatorPresenceSettings({ operator_persona_enabled: false })).toEqual({
      operator_persona_enabled: false,
      spoken_alerts_enabled: true,
      privacy_mode: false,
      mobile_compact_preferred: true,
      kairo_narration: 'conversational',
      ide_voice_strip_enabled: false,
    });
  });

  it('normalizes ide voice strip opt-in', () => {
    expect(normalizeOperatorPresenceSettings({ ide_voice_strip_enabled: true })).toEqual({
      ...defaultOperatorPresenceSettings(),
      ide_voice_strip_enabled: true,
    });
  });
});
