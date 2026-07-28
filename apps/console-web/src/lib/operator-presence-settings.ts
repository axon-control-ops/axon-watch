import type {
  AutonomyMode,
  OperatorPresenceSettings,
  SttMode,
  VoiceRoutingMode,
} from '../contracts/canonical';

export const OPERATOR_PRESENCE_SETTINGS_KEY = 'axon-x:operator-presence-settings';

/** axon-local desktop voice deck defaults. */
export const DEFAULT_SPEECH_RATE = 1.0;
export const DEFAULT_SPEECH_PITCH = 1.04;
export const DEFAULT_AZURE_VOICE_ID = 'en-GB-RyanNeural';
export const DEFAULT_STT_MODE: SttMode = 'cloud';
export const DEFAULT_VOICE_ROUTING_MODE: VoiceRoutingMode = 'runtime_on_deep';
export const DEFAULT_VAXON_MODEL_ID = 'gpt-5.4-high';
export const DEFAULT_AUTONOMY_MODE: AutonomyMode = 'manual';

export const VAXON_MODEL_OPTIONS = [
  { id: 'gpt-5.4-high', label: 'GPT-5.4 High' },
  { id: 'composer-2', label: 'Composer 2' },
  { id: 'claude-sonnet-5-thinking-high', label: 'Claude Sonnet 5 Thinking High' },
] as const;

export function defaultOperatorPresenceSettings(): OperatorPresenceSettings {
  return {
    operator_persona_enabled: true,
    spoken_alerts_enabled: true,
    privacy_mode: false,
    mobile_compact_preferred: true,
    kairo_narration: 'conversational',
    ide_voice_strip_enabled: false,
    hands_free_enabled: false,
    // JARVIS duplex: after VAXON speaks, listen for a natural reply.
    proactive_duplex_enabled: true,
    autonomy_mode: DEFAULT_AUTONOMY_MODE,
    speech_rate: DEFAULT_SPEECH_RATE,
    speech_pitch: DEFAULT_SPEECH_PITCH,
    azure_voice_id: DEFAULT_AZURE_VOICE_ID,
    stt_mode: DEFAULT_STT_MODE,
    voice_routing_mode: DEFAULT_VOICE_ROUTING_MODE,
    vaxon_model_id: DEFAULT_VAXON_MODEL_ID,
    narrate_tool_progress: false,
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

function normalizeAzureVoiceId(raw: unknown): string {
  const value = String(raw ?? '').trim();
  return value || DEFAULT_AZURE_VOICE_ID;
}

function normalizeSttMode(raw: unknown): SttMode {
  const value = String(raw ?? '').trim().toLowerCase();
  if (value === 'browser' || value === 'browser_continuous' || value === 'cloud') {
    return value;
  }
  return DEFAULT_STT_MODE;
}

function normalizeVoiceRoutingMode(raw: unknown): VoiceRoutingMode {
  const value = String(raw ?? '').trim().toLowerCase();
  if (
    value === 'template_first' ||
    value === 'runtime_on_deep' ||
    value === 'runtime_aggressive'
  ) {
    return value;
  }
  return DEFAULT_VOICE_ROUTING_MODE;
}

function normalizeVaxonModelId(raw: unknown): string {
  const value = String(raw ?? '').trim();
  if (!value) {
    return DEFAULT_VAXON_MODEL_ID;
  }
  const allowed = new Set<string>(VAXON_MODEL_OPTIONS.map((row) => row.id));
  if (allowed.has(value)) {
    return value;
  }
  // Accept catalog ids that match the VAXON allowlist by prefix (env-extended pools).
  if (/^[a-z0-9][a-z0-9._-]{1,118}$/i.test(value)) {
    return value.slice(0, 120);
  }
  return DEFAULT_VAXON_MODEL_ID;
}

function normalizeAutonomyMode(raw: unknown): AutonomyMode {
  const value = String(raw ?? '').trim().toLowerCase();
  if (value === 'manual' || value === 'semi' || value === 'full') {
    return value;
  }
  return DEFAULT_AUTONOMY_MODE;
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
    proactive_duplex_enabled:
      raw.proactive_duplex_enabled ?? defaults.proactive_duplex_enabled,
    autonomy_mode: normalizeAutonomyMode(raw.autonomy_mode ?? defaults.autonomy_mode),
    speech_rate: normalizeSpeechRate(raw.speech_rate ?? defaults.speech_rate),
    speech_pitch: normalizeSpeechPitch(raw.speech_pitch ?? defaults.speech_pitch),
    azure_voice_id: normalizeAzureVoiceId(raw.azure_voice_id ?? defaults.azure_voice_id),
    stt_mode: normalizeSttMode(raw.stt_mode ?? defaults.stt_mode),
    voice_routing_mode: normalizeVoiceRoutingMode(
      raw.voice_routing_mode ?? defaults.voice_routing_mode,
    ),
    vaxon_model_id: normalizeVaxonModelId(raw.vaxon_model_id ?? defaults.vaxon_model_id),
    narrate_tool_progress: raw.narrate_tool_progress ?? defaults.narrate_tool_progress,
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

export function applyJarvisDuplexPreset(
  settings: OperatorPresenceSettings,
  enabled: boolean,
): OperatorPresenceSettings {
  if (!enabled) {
    return normalizeOperatorPresenceSettings({
      ...settings,
      proactive_duplex_enabled: false,
    });
  }
  return normalizeOperatorPresenceSettings({
    ...settings,
    proactive_duplex_enabled: true,
    hands_free_enabled: true,
    spoken_alerts_enabled: true,
    privacy_mode: false,
    stt_mode: 'cloud',
    kairo_narration:
      settings.kairo_narration === 'off' ? 'conversational' : settings.kairo_narration,
  });
}

/** Format like axon-local mono readout (`1.00`). */
export function formatVoiceTuningValue(value: number): string {
  return value.toFixed(2);
}
