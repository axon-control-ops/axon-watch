/**
 * Local desktop wake-word engine contract.
 *
 * Pre-wake audio stays in a bounded in-memory ring buffer and is never uploaded.
 * Cloud/browser STT starts only after a wake (or an explicit follow-up window).
 */

export type WakeWordEngineStatus =
  | 'unavailable'
  | 'disabled'
  | 'consent_required'
  | 'starting'
  | 'listening'
  | 'woke'
  | 'error'
  | 'privacy_muted';

export type WakeWordSensitivity = 'low' | 'medium' | 'high';

export interface WakeWordDetection {
  at: number;
  keyword: string;
  confidence: number;
  /** Milliseconds of local audio retained after wake for STT handoff. */
  utteranceBufferMs: number;
}

export interface WakeWordEngineOptions {
  keyword?: string;
  sensitivity?: WakeWordSensitivity;
  /** Explicit always-listening consent from operator settings. */
  consentGranted: boolean;
  privacyMuted: boolean;
  onStatus?: (status: WakeWordEngineStatus, detail?: string) => void;
  onWake?: (detection: WakeWordDetection) => void;
}

export interface WakeWordEngine {
  readonly id: string;
  readonly label: string;
  status(): WakeWordEngineStatus;
  start(options: WakeWordEngineOptions): Promise<void>;
  stop(): Promise<void>;
  /** Drop ring buffer + stop capture immediately. */
  mutePrivacy(): Promise<void>;
}

export interface WakeWordBenchmarkResult {
  engineId: string;
  latencyMsP50: number | null;
  falseWakePerHour: number | null;
  missRate: number | null;
  cpuPercentApprox: number | null;
  license: string;
  customKeywordSupport: boolean;
  webkitGtkCompatible: boolean | null;
  notes: string;
}

/** Benchmark spike notes — no proprietary key dependency by default. */
export const WAKE_WORD_ENGINE_BENCHMARKS: readonly WakeWordBenchmarkResult[] = [
  {
    engineId: 'openwakeword-wasm',
    latencyMsP50: null,
    falseWakePerHour: null,
    missRate: null,
    cpuPercentApprox: null,
    license: 'Apache-2.0',
    customKeywordSupport: true,
    webkitGtkCompatible: null,
    notes:
      'Preferred open-source candidate for custom “VAXON” once WASM packaging proves on WebKitGTK.',
  },
  {
    engineId: 'porcupine',
    latencyMsP50: null,
    falseWakePerHour: null,
    missRate: null,
    cpuPercentApprox: null,
    license: 'Proprietary (Picovoice)',
    customKeywordSupport: true,
    webkitGtkCompatible: null,
    notes: 'Not default — requires access key; keep as optional adapter only.',
  },
  {
    engineId: 'browser-energy-gate',
    latencyMsP50: 80,
    falseWakePerHour: null,
    missRate: null,
    cpuPercentApprox: 2,
    license: 'Apache-2.0 (Axon-X)',
    customKeywordSupport: false,
    webkitGtkCompatible: true,
    notes:
      'Interim local gate: energy VAD + existing transcript wake-word regex after mic opens. Not true always-on keyword spotting.',
  },
];

export function selectDefaultWakeWordEngineId(): string {
  // Evidence gate: only promote openwakeword-wasm after packaged false-wake/CPU soak.
  return 'browser-energy-gate';
}
