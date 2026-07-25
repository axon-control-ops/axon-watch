export type KairoNarrationLevel = 'off' | 'minimal' | 'conversational';
export type VoiceRoutingMode = 'template_first' | 'runtime_on_deep' | 'runtime_aggressive';
export type SttMode = 'browser' | 'browser_continuous' | 'cloud';

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
  /**
   * JARVIS duplex: after unsolicited speech, listen for a reply without wake word
   * (uses the follow-up window). Implies hands-free once voice is unlocked.
   */
  proactive_duplex_enabled: boolean;
  /** Azure + browser speech rate (1.0 = engine default). */
  speech_rate: number;
  /** Azure + browser speech pitch (1.04 = axon-local Azure default). */
  speech_pitch: number;
  /** Azure neural voice id for VAXON TTS. */
  azure_voice_id: string;
  /** Speech-to-text adapter mode (browser default; cloud optional). */
  stt_mode: SttMode;
  /** Independent VAXON voice routing (not IDE Composer). */
  voice_routing_mode: VoiceRoutingMode;
  /** Speak tool milestones during agent runs (conversational only). */
  narrate_tool_progress: boolean;
}

/** Plain-English alert guide (control-plane authority; console may fall back locally). */
export interface OperatorAlertExplanation {
  what: string;
  you_do: string;
  agent_do: string;
  spoken: string;
}

export interface SpokenAlertEligibility {
  eligible: boolean;
  reason: string;
  signal_id: string | null;
  message: string;
  /** Present when eligible; null when blocked / no interruptive signal. */
  explanation?: OperatorAlertExplanation | null;
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
