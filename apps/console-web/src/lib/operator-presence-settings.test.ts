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
      hands_free_enabled: false,
      proactive_duplex_enabled: true,
      autonomy_mode: 'manual',
      speech_rate: 1.0,
      speech_pitch: 1.04,
      azure_voice_id: 'en-GB-RyanNeural',
      stt_mode: 'cloud',
      voice_routing_mode: 'runtime_on_deep',
      narrate_tool_progress: false,
      vaxon_model_id: 'gpt-5.4-high',
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
      hands_free_enabled: false,
      proactive_duplex_enabled: true,
      autonomy_mode: 'manual',
      speech_rate: 1.0,
      speech_pitch: 1.04,
      azure_voice_id: 'en-GB-RyanNeural',
      stt_mode: 'cloud',
      voice_routing_mode: 'runtime_on_deep',
      narrate_tool_progress: false,
      vaxon_model_id: 'gpt-5.4-high',
    });
  });

  it('normalizes autonomy modes', () => {
    expect(normalizeOperatorPresenceSettings({ autonomy_mode: 'semi' }).autonomy_mode).toBe(
      'semi',
    );
    expect(normalizeOperatorPresenceSettings({ autonomy_mode: 'full' }).autonomy_mode).toBe(
      'full',
    );
    expect(
      normalizeOperatorPresenceSettings({
        autonomy_mode: 'nope' as 'manual',
      }).autonomy_mode,
    ).toBe('manual');
  });

  it('normalizes continuous speech rate and pitch like axon-local', () => {
    expect(normalizeOperatorPresenceSettings({ speech_rate: 0.85 }).speech_rate).toBe(0.85);
    expect(normalizeOperatorPresenceSettings({ speech_pitch: 1.12 }).speech_pitch).toBe(1.12);
    expect(normalizeOperatorPresenceSettings({ speech_rate: 9.99 }).speech_rate).toBe(1.3);
    expect(normalizeOperatorPresenceSettings({ speech_pitch: -1 }).speech_pitch).toBe(0.5);
  });

  it('normalizes ide voice strip opt-in', () => {
    expect(normalizeOperatorPresenceSettings({ ide_voice_strip_enabled: true })).toEqual({
      ...defaultOperatorPresenceSettings(),
      ide_voice_strip_enabled: true,
    });
  });

  it('defaults and accepts VAXON model ids independently of workspace composer', () => {
    expect(normalizeOperatorPresenceSettings({}).vaxon_model_id).toBe('gpt-5.4-high');
    expect(
      normalizeOperatorPresenceSettings({ vaxon_model_id: 'composer-2' }).vaxon_model_id,
    ).toBe('composer-2');
  });
});
