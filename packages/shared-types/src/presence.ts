export type KairoNarrationLevel = 'off' | 'minimal' | 'conversational';

export interface OperatorPresenceSettings {
  operator_persona_enabled: boolean;
  spoken_alerts_enabled: boolean;
  privacy_mode: boolean;
  mobile_compact_preferred: boolean;
  kairo_narration: KairoNarrationLevel;
  ide_voice_strip_enabled: boolean;
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
