import { ref } from 'vue';

import { logKairoVoice } from '../../lib/kairo-voice-debug';
import { isKairoVoiceSpeaking } from '../../lib/kairo-voice-playback';
import { openKairoVoiceFollowupWindow } from '../../lib/kairo-voice-followup-window';
import { normalizeVoiceTranscript } from '../../lib/kairo-entity-labels';
import {
  detectVoiceInterruptPhrase,
  evaluateVoiceTranscript,
  type KairoVoiceCaptureMode,
} from '../../lib/kairo-voice-gate';
import { isSpeechCaptureSupported, SpeechCaptureSession } from './speech-capture';
import { CloudAudioCaptureSession, isCloudAudioCaptureSupported } from './cloud-audio-capture';
import {
  probeCloudSttAvailability,
  resolveSttCaptureMode,
  transcribeCloudStt,
} from '../../lib/kairo-cloud-stt';
import { submitKairoConversationTranscript } from './kairo-conversation-bus';
import { kairoConversationPhase, setKairoConversationPhase } from './kairo-conversation-state';

const session = new SpeechCaptureSession();
const cloudSession = new CloudAudioCaptureSession();

export const kairoCaptureCapturing = ref(false);
export const kairoCaptureInterim = ref('');
export const kairoCaptureError = ref<string | null>(null);
export const kairoCaptureMode = ref<KairoVoiceCaptureMode>('manual');
export const kairoCaptureLastHeard = ref('');
export const kairoCaptureLastGateReason = ref<string | null>(null);
export const kairoCaptureLastAccepted = ref<boolean | null>(null);
export const kairoCaptureLastSubmitState = ref<'submitted' | 'queued' | 'ignored' | 'dropped' | null>(null);

let privacyBlocked: () => boolean = () => false;
let sttMode: () => string = () => 'browser';
let onVoiceInterrupt: () => void = () => {};
let onCaptureEnd: () => void = () => {};
const captureEndListeners = new Set<() => void>();

let bargeInTriggered = false;
let activeCaptureProvider: 'browser' | 'cloud' | null = null;

export function registerKairoCaptureEndListener(listener: () => void): () => void {
  captureEndListeners.add(listener);
  return () => {
    captureEndListeners.delete(listener);
  };
}

export function registerKairoVoiceInterruptHandler(handler: () => void): () => void {
  onVoiceInterrupt = handler;
  return () => {
    if (onVoiceInterrupt === handler) {
      onVoiceInterrupt = () => {};
    }
  };
}

export function setKairoSpeechPrivacyBlocked(check: () => boolean): void {
  privacyBlocked = check;
}

export function setKairoSpeechSttMode(check: () => string): void {
  sttMode = check;
}

function notifyCaptureEnd(): void {
  onCaptureEnd();
  for (const listener of captureEndListeners) {
    listener();
  }
}

export function isKairoSpeechCaptureSupported(): boolean {
  return isSpeechCaptureSupported();
}

function mapCaptureError(code: string): string | null {
  if (code === 'aborted' || code === 'no-speech') {
    return null;
  }
  if (code === 'not-allowed') {
    return 'Microphone permission denied — allow mic access for this site.';
  }
  if (code === 'network') {
    return 'Speech recognition needs network access.';
  }
  if (code === 'start_failed') {
    return 'Could not start speech recognition — try again.';
  }
  if (code === 'phrases-not-supported') {
    return 'Speech engine rejected phrase bias — refresh and try again.';
  }
  if (code === 'language-not-supported') {
    return 'Speech language not supported — falling back to en-US.';
  }
  return `Speech capture failed (${code}).`;
}

export function canStartKairoSpeechCapture(): boolean {
  return (
    isKairoSpeechCaptureSupported() &&
    !privacyBlocked() &&
    !kairoCaptureCapturing.value &&
    kairoConversationPhase.value !== 'thinking' &&
    kairoConversationPhase.value !== 'speaking'
  );
}

function triggerVoiceInterrupt(source: 'interim' | 'final'): void {
  if (bargeInTriggered) {
    return;
  }
  bargeInTriggered = true;
  logKairoVoice('interrupt', { source, mode: kairoCaptureMode.value });
  onVoiceInterrupt();
  setKairoConversationPhase('idle');
}

function handleInterimTranscript(transcript: string, mode: KairoVoiceCaptureMode): void {
  const normalized = normalizeVoiceTranscript(transcript);
  kairoCaptureInterim.value = normalized;
  if (mode !== 'barge_in') {
    return;
  }
  const trimmed = normalized.trim();
  if (trimmed.length < 3) {
    return;
  }
  if (detectVoiceInterruptPhrase(trimmed)) {
    triggerVoiceInterrupt('interim');
    stopKairoSpeechCapture();
  }
}

async function handleFinalTranscript(transcript: string, mode: KairoVoiceCaptureMode): Promise<void> {
  kairoCaptureInterim.value = '';
  kairoCaptureCapturing.value = false;
  kairoCaptureLastHeard.value = normalizeVoiceTranscript(transcript).trim();

  if (isKairoVoiceSpeaking() || kairoConversationPhase.value === 'speaking') {
    kairoCaptureLastAccepted.value = false;
    kairoCaptureLastGateReason.value = 'voice_output_active';
    kairoCaptureLastSubmitState.value = 'dropped';
    logKairoVoice('final_dropped', {
      transcript,
      mode,
      reason: 'voice_output_active',
    });
    if (kairoConversationPhase.value === 'listening') {
      setKairoConversationPhase('idle');
    }
    notifyCaptureEnd();
    return;
  }

  if (kairoConversationPhase.value === 'thinking') {
    if (detectVoiceInterruptPhrase(normalizeVoiceTranscript(transcript))) {
      triggerVoiceInterrupt('final');
    }
    kairoCaptureLastAccepted.value = false;
    kairoCaptureLastGateReason.value = 'thinking';
    kairoCaptureLastSubmitState.value = 'dropped';
    kairoCaptureCapturing.value = false;
    notifyCaptureEnd();
    return;
  }

  const gate = evaluateVoiceTranscript(transcript, mode);
  logKairoVoice('final', {
    transcript,
    mode,
    accept: gate.accept,
    reason: gate.reason,
    shouldInterrupt: gate.shouldInterrupt,
  });
  kairoCaptureLastAccepted.value = gate.accept;
  kairoCaptureLastGateReason.value = gate.reason;

  if (gate.shouldInterrupt) {
    triggerVoiceInterrupt('final');
  }

  if (!gate.accept || !gate.submitContent) {
    kairoCaptureLastSubmitState.value = 'ignored';
    if (kairoConversationPhase.value === 'listening') {
      setKairoConversationPhase('idle');
    }
    notifyCaptureEnd();
    return;
  }

  // Keep the post-reply follow-up window open across TTS so "repeat that" works.
  if (mode === 'hands_free') {
    openKairoVoiceFollowupWindow();
  }

  kairoCaptureLastSubmitState.value = await submitKairoConversationTranscript(gate.submitContent, {
    voiceCaptureMode: mode,
  });
  notifyCaptureEnd();
}

function shouldUseCloudCapture(mode: KairoVoiceCaptureMode): boolean {
  return (
    resolveSttCaptureMode(sttMode(), privacyBlocked()) === 'cloud' &&
    mode === 'manual' &&
    isCloudAudioCaptureSupported()
  );
}

function startBrowserCapture(mode: KairoVoiceCaptureMode): boolean {
  const started = session.start({
    onInterim: (transcript) => {
      handleInterimTranscript(transcript, mode);
    },
    onFinal: (transcript) => {
      void handleFinalTranscript(transcript, mode);
    },
    onError: (code) => {
      kairoCaptureCapturing.value = false;
      kairoCaptureInterim.value = '';
      kairoCaptureError.value = mapCaptureError(code);
      setKairoConversationPhase('idle');
      notifyCaptureEnd();
    },
    onEnd: () => {
      const pendingTranscript = kairoCaptureInterim.value.trim();
      kairoCaptureCapturing.value = false;
      kairoCaptureInterim.value = '';
      if (pendingTranscript && !bargeInTriggered) {
        void handleFinalTranscript(pendingTranscript, kairoCaptureMode.value);
        return;
      }
      if (kairoConversationPhase.value === 'listening') {
        setKairoConversationPhase('idle');
      }
      notifyCaptureEnd();
    },
  });

  kairoCaptureCapturing.value = started;
  activeCaptureProvider = started ? 'browser' : null;
  if (!started) {
    setKairoConversationPhase('idle');
  } else {
    logKairoVoice('capture_start', { mode, provider: 'browser' });
  }
  return started;
}

async function finishCloudCapture(mode: KairoVoiceCaptureMode): Promise<void> {
  const blob = await cloudSession.stop();
  kairoCaptureCapturing.value = false;
  activeCaptureProvider = null;
  kairoCaptureInterim.value = '';
  if (!blob) {
    kairoCaptureError.value = 'No audio captured — try again.';
    setKairoConversationPhase('idle');
    notifyCaptureEnd();
    return;
  }

  const result = await transcribeCloudStt(blob, { privacyBlocked: privacyBlocked() });
  if (!result.transcript.trim()) {
    if (result.reason !== 'privacy_mode' && isSpeechCaptureSupported()) {
      logKairoVoice('cloud_stt_fallback', { mode, reason: result.reason });
      const started = startBrowserCapture(mode);
      if (started) {
        return;
      }
    }
    kairoCaptureError.value =
      result.reason === 'privacy_mode'
        ? null
        : 'Cloud speech could not transcribe that clip — try again or switch to browser STT.';
    setKairoConversationPhase('idle');
    notifyCaptureEnd();
    return;
  }

  logKairoVoice('cloud_stt_ok', {
    mode,
    provider: result.provider,
    confidence: result.confidence,
  });
  await handleFinalTranscript(result.transcript, mode);
}

async function startCloudCapture(mode: KairoVoiceCaptureMode): Promise<boolean> {
  const probe = await probeCloudSttAvailability();
  if (!probe.available) {
    return startBrowserCapture(mode);
  }
  const started = await cloudSession.start();
  if (!started) {
    return startBrowserCapture(mode);
  }
  kairoCaptureCapturing.value = true;
  activeCaptureProvider = 'cloud';
  logKairoVoice('capture_start', { mode, provider: 'cloud' });
  return true;
}

export function startKairoSpeechCapture(
  mode: KairoVoiceCaptureMode = 'manual',
  options?: { takeover?: boolean },
): boolean {
  if (kairoConversationPhase.value === 'thinking' || kairoConversationPhase.value === 'speaking') {
    return false;
  }
  if (options?.takeover && kairoCaptureCapturing.value) {
    // Space / Mic PTT while hands-free is already open — drop ambient session first.
    session.stopImmediate();
    cloudSession.stopImmediate();
    kairoCaptureCapturing.value = false;
    activeCaptureProvider = null;
    kairoCaptureInterim.value = '';
  }
  if (!canStartKairoSpeechCapture()) {
    return false;
  }

  kairoCaptureMode.value = mode;
  bargeInTriggered = false;
  kairoCaptureError.value = null;
  kairoCaptureInterim.value = '';
  // Ambient hands-free capture is a standing input capability, not an active
  // conversation turn. Only explicit manual PTT owns the visible LISTENING
  // phase; otherwise Chromium's normal no-speech end/restart cycle makes the
  // whole IDE alternate between voice and attention profiles every second.
  if (mode === 'manual') {
    setKairoConversationPhase('listening');
  }

  if (shouldUseCloudCapture(mode)) {
    void startCloudCapture(mode).then((started) => {
      if (!started) {
        kairoCaptureCapturing.value = false;
        if (kairoConversationPhase.value === 'listening') {
          setKairoConversationPhase('idle');
        }
      }
    });
    return true;
  }

  return startBrowserCapture(mode);
}

export function stopKairoSpeechCapture(): void {
  if (activeCaptureProvider === 'cloud' && kairoCaptureCapturing.value) {
    void finishCloudCapture(kairoCaptureMode.value);
    return;
  }
  session.stop();
}
