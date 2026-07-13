import { pickBestSpeechTranscript } from '../../lib/operator-persona-stt-aliases';
import { applySpeechRecognitionBias } from './speech-recognition-bias';

export type SpeechCaptureCallbacks = {
  onInterim?: (transcript: string) => void;
  onFinal: (transcript: string) => void;
  onError?: (code: string) => void;
  onEnd?: () => void;
};

type BrowserSpeechRecognition = {
  lang: string;
  interimResults: boolean;
  maxAlternatives: number;
  continuous?: boolean;
  start: () => void;
  stop: () => void;
  onresult: ((event: SpeechRecognitionEvent) => void) | null;
  onerror: ((event: SpeechRecognitionErrorEvent) => void) | null;
  onend: (() => void) | null;
};

type BrowserSpeechRecognitionConstructor = new () => BrowserSpeechRecognition;

/** Chromium often rejects regional English tags like en-ZA with language-not-supported. */
const WELL_SUPPORTED_ENGLISH_LANGS = new Set([
  'en-US',
  'en-GB',
  'en-AU',
  'en-CA',
  'en-IN',
  'en-IE',
  'en-NZ',
]);

/** Ordered fallbacks when the engine rejects the preferred language. */
const SPEECH_LANG_FALLBACKS = ['en-US', 'en-GB', 'en'] as const;

function speechRecognitionCtor(): BrowserSpeechRecognitionConstructor | null {
  if (typeof window === 'undefined') {
    return null;
  }
  const win = window as Window & {
    SpeechRecognition?: BrowserSpeechRecognitionConstructor;
    webkitSpeechRecognition?: BrowserSpeechRecognitionConstructor;
  };
  return win.SpeechRecognition ?? win.webkitSpeechRecognition ?? null;
}

export function isSpeechCaptureSupported(): boolean {
  return speechRecognitionCtor() !== null;
}

export function resolveSpeechRecognitionLang(
  preferred?: string | null,
): string {
  const raw =
    (preferred ?? (typeof navigator !== 'undefined' ? navigator.language : '') ?? '')
      .trim() || 'en-US';
  if (WELL_SUPPORTED_ENGLISH_LANGS.has(raw)) {
    return raw;
  }
  // Any other en-* (e.g. en-ZA) → en-US. Non-English also falls back for VAXON English ops.
  return 'en-US';
}

export function speechRecognitionLangCandidates(preferred?: string | null): string[] {
  const primary = resolveSpeechRecognitionLang(preferred);
  const ordered = [primary, ...SPEECH_LANG_FALLBACKS];
  const seen = new Set<string>();
  const out: string[] = [];
  for (const lang of ordered) {
    if (!lang || seen.has(lang)) {
      continue;
    }
    seen.add(lang);
    out.push(lang);
  }
  return out;
}

function transcriptFromResult(result: SpeechRecognitionResult): string {
  const alternatives: string[] = [];
  for (let index = 0; index < result.length; index += 1) {
    const transcript = result[index]?.transcript?.trim();
    if (transcript) {
      alternatives.push(transcript);
    }
  }
  return pickBestSpeechTranscript(alternatives);
}

export class SpeechCaptureSession {
  private recognition: BrowserSpeechRecognition | null = null;

  private stopRequested = false;

  private langAttemptIndex = 0;

  private langCandidates: string[] = ['en-US'];

  /** Bumped on stop so stale onerror/onend from aborted engines are ignored. */
  private sessionEpoch = 0;

  start(callbacks: SpeechCaptureCallbacks): boolean {
    const Ctor = speechRecognitionCtor();
    if (!Ctor) {
      return false;
    }
    // Drop any prior engine without bumping epoch twice.
    this.invalidateActiveRecognition();
    this.stopRequested = false;
    this.langAttemptIndex = 0;
    this.langCandidates = speechRecognitionLangCandidates();
    const epoch = this.sessionEpoch;
    return this.beginRecognition(Ctor, callbacks, this.langCandidates[0] ?? 'en-US', epoch);
  }

  private invalidateActiveRecognition(): void {
    this.sessionEpoch += 1;
    this.stopRequested = true;
    if (!this.recognition) {
      return;
    }
    const recognition = this.recognition;
    this.recognition = null;
    try {
      const abortable = recognition as BrowserSpeechRecognition & { abort?: () => void };
      if (typeof abortable.abort === 'function') {
        abortable.abort();
      } else {
        recognition.stop();
      }
    } catch {
      // already stopped
    }
  }

  private beginRecognition(
    Ctor: BrowserSpeechRecognitionConstructor,
    callbacks: SpeechCaptureCallbacks,
    lang: string,
    epoch: number,
  ): boolean {
    if (epoch !== this.sessionEpoch) {
      return false;
    }
    const recognition = new Ctor();
    this.recognition = recognition;
    recognition.lang = lang;
    recognition.interimResults = true;
    recognition.maxAlternatives = 5;
    recognition.continuous = true;
    applySpeechRecognitionBias(recognition);

    let settled = false;
    const finishEnd = (): void => {
      if (settled || epoch !== this.sessionEpoch) {
        return;
      }
      settled = true;
      if (this.recognition === recognition) {
        this.recognition = null;
      }
      callbacks.onEnd?.();
    };

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      if (epoch !== this.sessionEpoch || this.recognition !== recognition) {
        return;
      }
      let interim = '';
      let finalText = '';
      for (let index = event.resultIndex; index < event.results.length; index += 1) {
        const result = event.results[index];
        if (!result) {
          continue;
        }
        const transcript = transcriptFromResult(result);
        if (!transcript) {
          continue;
        }
        if (result.isFinal) {
          finalText = `${finalText} ${transcript}`.trim();
        } else {
          interim = `${interim} ${transcript}`.trim();
        }
      }
      if (interim) {
        callbacks.onInterim?.(interim);
      }
      if (finalText) {
        callbacks.onFinal(finalText);
        this.stopRequested = true;
        recognition.stop();
      }
    };

    recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
      if (epoch !== this.sessionEpoch || this.recognition !== recognition) {
        return;
      }
      const code = String(event.error || 'unknown');
      if (
        code === 'language-not-supported' &&
        !this.stopRequested &&
        this.langAttemptIndex < this.langCandidates.length - 1
      ) {
        this.langAttemptIndex += 1;
        const nextLang = this.langCandidates[this.langAttemptIndex] ?? 'en-US';
        this.recognition = null;
        this.beginRecognition(Ctor, callbacks, nextLang, epoch);
        return;
      }
      if (this.recognition === recognition) {
        this.recognition = null;
      }
      // Benign end conditions — treat as clean end, not a hard failure.
      if (code === 'aborted' || code === 'no-speech') {
        finishEnd();
        return;
      }
      if (!this.stopRequested) {
        settled = true;
        callbacks.onError?.(code);
      }
    };

    recognition.onend = () => {
      finishEnd();
    };

    try {
      recognition.start();
      return true;
    } catch {
      if (epoch !== this.sessionEpoch) {
        return false;
      }
      this.recognition = null;
      if (this.langAttemptIndex < this.langCandidates.length - 1) {
        this.langAttemptIndex += 1;
        const nextLang = this.langCandidates[this.langAttemptIndex] ?? 'en-US';
        return this.beginRecognition(Ctor, callbacks, nextLang, epoch);
      }
      callbacks.onError?.('start_failed');
      return false;
    }
  }

  stop(): void {
    this.invalidateActiveRecognition();
  }

  /**
   * Abort the current recognition so a new session can start immediately
   * (Space PTT while hands-free is already capturing).
   */
  stopImmediate(): void {
    this.invalidateActiveRecognition();
  }
}
