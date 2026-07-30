import { beforeEach, describe, expect, it, vi } from 'vitest';

import {
  enqueueSpeech,
  isSpeechQueueBusy,
  isSpeechQueueSpeaking,
  stopSpeech,
  subscribeSpeechQueueSpeaking,
  waitForSpeechQueueIdle,
  type SpeechPort,
} from './speech-queue';

class MockUtterance {
  rate = 0;
  pitch = 0;
  volume = 0;
  voice: SpeechSynthesisVoice | null = null;
  onend?: () => void;
  onerror?: () => void;

  constructor(public text = '') {}
}

function createSpeechPort(): SpeechPort & { utterances: MockUtterance[] } {
  const utterances: MockUtterance[] = [];
  return {
    utterances,
    speak(utterance: SpeechSynthesisUtterance) {
      utterances.push(utterance as unknown as MockUtterance);
    },
    cancel: vi.fn(),
    getVoices: () => [],
  };
}

describe('speech queue', () => {
  beforeEach(() => {
    vi.stubGlobal('SpeechSynthesisUtterance', MockUtterance);
  });

  it('serializes speech and supports interrupt', () => {
    vi.useFakeTimers();
    const speech = createSpeechPort();
    stopSpeech(speech);

    enqueueSpeech('first line', speech);
    expect(isSpeechQueueSpeaking()).toBe(true);
    vi.advanceTimersByTime(220);
    expect(speech.utterances).toHaveLength(1);

    stopSpeech(speech);
    expect(isSpeechQueueSpeaking()).toBe(false);
    expect(speech.cancel).toHaveBeenCalled();
    vi.useRealTimers();
  });

  it('waitForSpeechQueueIdle resolves after utterance ends', async () => {
    vi.useFakeTimers();
    const speech = createSpeechPort();
    stopSpeech(speech);

    enqueueSpeech('hello operator', speech);
    const idle = waitForSpeechQueueIdle();
    expect(isSpeechQueueBusy()).toBe(true);

    vi.advanceTimersByTime(220);
    const utterance = speech.utterances[0];
    utterance.onend?.();
    await vi.advanceTimersByTimeAsync(300);
    await idle;

    expect(isSpeechQueueBusy()).toBe(false);
    vi.useRealTimers();
  });

  it('notifies speaking subscribers', () => {
    const speech = createSpeechPort();
    const states: boolean[] = [];
    const unsubscribe = subscribeSpeechQueueSpeaking((active) => {
      states.push(active);
    });

    stopSpeech(speech);
    enqueueSpeech('hello', speech);
    stopSpeech(speech);
    unsubscribe();

    expect(states).toContain(true);
    expect(states.at(-1)).toBe(false);
  });

  it('defaults browser fallback to axon-local rate/pitch', () => {
    vi.useFakeTimers();
    const speech = createSpeechPort();
    stopSpeech(speech);

    enqueueSpeech('natural voice', speech);
    vi.advanceTimersByTime(220);

    const utterance = speech.utterances[0] as MockUtterance;
    expect(utterance.rate).toBe(1.0);
    expect(utterance.pitch).toBe(1.04);
    expect(utterance.volume).toBe(1);
    vi.useRealTimers();
  });

  it('honors explicit speech rate and pitch for browser fallback', () => {
    vi.useFakeTimers();
    const speech = createSpeechPort();
    stopSpeech(speech);

    enqueueSpeech('slower voice', speech, { rate: 0.85, pitch: 1.12 });
    vi.advanceTimersByTime(220);

    const utterance = speech.utterances[0] as MockUtterance;
    expect(utterance.rate).toBe(0.85);
    expect(utterance.pitch).toBe(1.12);
    vi.useRealTimers();
  });

  it('selects a distinct browser voice from the employee voice hint', () => {
    vi.useFakeTimers();
    const speech = createSpeechPort();
    speech.getVoices = () =>
      [
        { name: 'Microsoft Davis', voiceURI: 'davis', lang: 'en-US' },
        { name: 'Microsoft Jenny', voiceURI: 'jenny', lang: 'en-US' },
      ] as SpeechSynthesisVoice[];
    stopSpeech(speech);

    enqueueSpeech('Cass reporting', speech, { voiceHint: 'en-US-DavisNeural' });
    vi.advanceTimersByTime(220);

    const utterance = speech.utterances[0] as MockUtterance;
    expect(utterance.voice?.name).toBe('Microsoft Davis');
    vi.useRealTimers();
  });

  it('maps SoniaNeural to a female browser voice when Sonia is missing', () => {
    vi.useFakeTimers();
    const speech = createSpeechPort();
    speech.getVoices = () =>
      [
        { name: 'Google UK English Male', voiceURI: 'uk-male', lang: 'en-GB' },
        { name: 'Google UK English Female', voiceURI: 'uk-female', lang: 'en-GB' },
      ] as SpeechSynthesisVoice[];
    stopSpeech(speech);

    enqueueSpeech('Mira reporting', speech, { voiceHint: 'en-GB-SoniaNeural' });
    vi.advanceTimersByTime(220);

    const utterance = speech.utterances[0] as MockUtterance;
    expect(utterance.voice?.name).toBe('Google UK English Female');
    vi.useRealTimers();
  });

  it('cancels delayed browser speech before it can start', () => {
    vi.useFakeTimers();
    const speech = createSpeechPort();
    stopSpeech(speech);

    enqueueSpeech('stale line', speech);
    stopSpeech(speech);
    vi.advanceTimersByTime(200);

    expect(speech.utterances).toHaveLength(0);
    expect(speech.cancel).toHaveBeenCalled();
    vi.useRealTimers();
  });

  it('prevents a canceled utterance from stealing the next reply start', () => {
    vi.useFakeTimers();
    const speech = createSpeechPort();
    stopSpeech(speech);

    enqueueSpeech('old line', speech);
    stopSpeech(speech);
    enqueueSpeech('fresh line', speech);
    vi.advanceTimersByTime(220);

    expect(speech.utterances).toHaveLength(1);
    expect(speech.utterances[0]?.text).toBe('\u200B\u200B\u200B\u2009\u2009fresh line');
    vi.useRealTimers();
  });
});
