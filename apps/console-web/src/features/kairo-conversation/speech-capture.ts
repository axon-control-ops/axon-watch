import { pickBestSpeechTranscript } from '../../lib/operator-persona-stt-aliases';

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

function resolveSpeechRecognitionLang(): string {
  if (typeof navigator === 'undefined') {
    return 'en-US';
  }
  const lang = navigator.language?.trim();
  if (lang && /^en(-|$)/i.test(lang)) {
    return lang;
  }
  return 'en-US';
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

  start(callbacks: SpeechCaptureCallbacks): boolean {
    const Ctor = speechRecognitionCtor();
    if (!Ctor || this.recognition) {
      return false;
    }

    this.stopRequested = false;
    const recognition = new Ctor();
    this.recognition = recognition;
    recognition.lang = resolveSpeechRecognitionLang();
    recognition.interimResults = true;
    recognition.maxAlternatives = 5;
    recognition.continuous = true;

    recognition.onresult = (event: SpeechRecognitionEvent) => {
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
      const code = String(event.error || 'unknown');
      if (!this.stopRequested || !['aborted', 'no-speech'].includes(code)) {
        callbacks.onError?.(code);
      }
    };

    recognition.onend = () => {
      this.recognition = null;
      callbacks.onEnd?.();
    };

    try {
      recognition.start();
      return true;
    } catch {
      this.recognition = null;
      callbacks.onError?.('start_failed');
      return false;
    }
  }

  stop(): void {
    this.stopRequested = true;
    if (this.recognition) {
      try {
        this.recognition.stop();
      } catch {
        this.recognition = null;
      }
    }
  }
}
