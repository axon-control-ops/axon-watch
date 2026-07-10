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
  onend?: () => void;
  onerror?: () => void;
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
    vi.advanceTimersByTime(60);
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

    vi.advanceTimersByTime(60);
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
});
