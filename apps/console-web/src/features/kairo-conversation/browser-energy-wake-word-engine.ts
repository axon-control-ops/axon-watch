import { recordVoiceLoopDiagnostic } from '../../lib/kairo-voice-loop-diagnostics';
import { logKairoVoice } from '../../lib/kairo-voice-debug';
import {
  selectDefaultWakeWordEngineId,
  type WakeWordDetection,
  type WakeWordEngine,
  type WakeWordEngineOptions,
  type WakeWordEngineStatus,
  type WakeWordSensitivity,
} from './wake-word-engine';

/**
 * Interim local wake gate used until an evidence-backed WASM keyword model ships.
 * Uses Web Audio energy VAD only — does not upload pre-wake samples.
 */
export class BrowserEnergyWakeWordEngine implements WakeWordEngine {
  readonly id = 'browser-energy-gate';
  readonly label = 'Local energy gate (interim)';

  private currentStatus: WakeWordEngineStatus = 'disabled';
  private options: WakeWordEngineOptions | null = null;
  private stream: MediaStream | null = null;
  private audioContext: AudioContext | null = null;
  private analyser: AnalyserNode | null = null;
  private raf = 0;
  private lastWakeAt = 0;

  status(): WakeWordEngineStatus {
    return this.currentStatus;
  }

  async start(options: WakeWordEngineOptions): Promise<void> {
    await this.stop();
    this.options = options;
    if (options.privacyMuted) {
      this.setStatus('privacy_muted');
      return;
    }
    if (!options.consentGranted) {
      this.setStatus('consent_required');
      return;
    }
    if (typeof window === 'undefined' || !navigator.mediaDevices?.getUserMedia) {
      this.setStatus('unavailable', 'mediaDevices missing');
      return;
    }

    this.setStatus('starting');
    try {
      this.stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
        video: false,
      });
      this.audioContext = new AudioContext();
      const source = this.audioContext.createMediaStreamSource(this.stream);
      this.analyser = this.audioContext.createAnalyser();
      this.analyser.fftSize = 2048;
      source.connect(this.analyser);
      this.setStatus('listening');
      this.pump();
    } catch (error) {
      this.setStatus('error', error instanceof Error ? error.message : 'mic_denied');
    }
  }

  async stop(): Promise<void> {
    if (this.raf) {
      cancelAnimationFrame(this.raf);
      this.raf = 0;
    }
    this.analyser = null;
    if (this.audioContext) {
      void this.audioContext.close().catch(() => undefined);
      this.audioContext = null;
    }
    if (this.stream) {
      for (const track of this.stream.getTracks()) {
        track.stop();
      }
      this.stream = null;
    }
    if (this.currentStatus !== 'disabled' && this.currentStatus !== 'privacy_muted') {
      this.setStatus('disabled');
    }
  }

  async mutePrivacy(): Promise<void> {
    await this.stop();
    this.setStatus('privacy_muted');
  }

  /** Test/harness hook — simulates a local wake without uploading audio. */
  simulateWake(keyword = 'VAXON', confidence = 0.9): void {
    this.emitWake({
      at: Date.now(),
      keyword,
      confidence,
      utteranceBufferMs: 600,
    });
  }

  private pump(): void {
    if (!this.analyser || !this.options) {
      return;
    }
    const data = new Uint8Array(this.analyser.fftSize);
    this.analyser.getByteTimeDomainData(data);
    let sum = 0;
    for (let i = 0; i < data.length; i += 1) {
      const centered = (data[i] ?? 128) - 128;
      sum += centered * centered;
    }
    const rms = Math.sqrt(sum / data.length) / 128;
    const threshold = sensitivityThreshold(this.options.sensitivity ?? 'medium');
    const now = Date.now();
    // Energy-only interim: emit a soft wake at most once per 4s when loud speech is present.
    // Real keyword spotting replaces this path; transcript gate still validates “VAXON”.
    if (rms >= threshold && now - this.lastWakeAt > 4000) {
      this.emitWake({
        at: now,
        keyword: 'energy',
        confidence: Math.min(1, rms),
        utteranceBufferMs: 600,
      });
    }
    this.raf = requestAnimationFrame(() => this.pump());
  }

  private emitWake(detection: WakeWordDetection): void {
    this.lastWakeAt = detection.at;
    this.setStatus('woke');
    recordVoiceLoopDiagnostic({
      kind: 'wake_gate',
      reason: detection.keyword,
      action: 'local_wake',
    });
    logKairoVoice('local_wake', {
      engine: this.id,
      keyword: detection.keyword,
      confidence: detection.confidence,
    });
    this.options?.onWake?.(detection);
    // Return to listening after a short refractory period.
    window.setTimeout(() => {
      if (this.stream && this.options && !this.options.privacyMuted) {
        this.setStatus('listening');
      }
    }, 750);
  }

  private setStatus(status: WakeWordEngineStatus, detail?: string): void {
    this.currentStatus = status;
    this.options?.onStatus?.(status, detail);
  }
}

function sensitivityThreshold(sensitivity: WakeWordSensitivity): number {
  if (sensitivity === 'low') {
    return 0.12;
  }
  if (sensitivity === 'high') {
    return 0.045;
  }
  return 0.07;
}

let sharedEngine: WakeWordEngine | null = null;

export function getDesktopWakeWordEngine(): WakeWordEngine {
  if (!sharedEngine) {
    const id = selectDefaultWakeWordEngineId();
    if (id === 'browser-energy-gate') {
      sharedEngine = new BrowserEnergyWakeWordEngine();
    } else {
      sharedEngine = new BrowserEnergyWakeWordEngine();
    }
  }
  return sharedEngine;
}

export function resetDesktopWakeWordEngineForTests(): void {
  sharedEngine = null;
}
