export type KairoNarrationLevel = 'off' | 'minimal' | 'conversational';

/**
 * Continuous speech tuning — axon-local parity (`voice_speech_rate` / `voice_speech_pitch`).
 * Rate: 0.50–1.30 · Pitch: 0.50–1.50
 */
export interface OperatorPresenceSettings {
  operator_persona_enabled: boolean;
  spoken_alerts_enabled: boolean;
  privacy_mode: boolean;
  mobile_compact_preferred: boolean;
  kairo_narration: KairoNarrationLevel;
  ide_voice_strip_enabled: boolean;
  hands_free_enabled: boolean;
  /** Azure + browser speech rate (1.0 = engine default). */
  speech_rate: number;
  /** Azure + browser speech pitch (1.04 = axon-local Azure default). */
  speech_pitch: number;
}

export interface SpokenAlertEligibility {
  eligible: boolean;
  reason: string;
  signal_id: string | null;
  message: string;
}

export interface OperatorPresenceMobile {
  compact_layout: boolean;
  foreground_only: boolean;
}

export type OperatorPresenceState =
  | 'idle'
  | 'observing'
  | 'alerting'
  | 'privacy_blocked';

export interface OperatorPresence {
  persona_voice_line: string;
  presence_state: OperatorPresenceState;
  settings: OperatorPresenceSettings;
  spoken_alert: SpokenAlertEligibility;
  mobile: OperatorPresenceMobile;
}
