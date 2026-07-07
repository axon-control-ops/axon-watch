import { beforeEach, describe, expect, it, vi } from 'vitest';

import {
  enqueueSpeech,
  isSpeechQueueSpeaking,
  stopSpeech,
  subscribeSpeechQueueSpeaking,
} from './speech-queue';

class MockUtterance {
  onend?: () => void;
  onerror?: () => void;
}

function createSpeechPort() {
  const utterances: MockUtterance[] = [];
  return {
    utterances,
    speak(utterance: MockUtterance) {
      utterances.push(utterance);
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
    const speech = createSpeechPort();
    stopSpeech(speech);

    enqueueSpeech('first line', speech);
    expect(isSpeechQueueSpeaking()).toBe(true);
    expect(speech.utterances).toHaveLength(1);

    stopSpeech(speech);
    expect(isSpeechQueueSpeaking()).toBe(false);
    expect(speech.cancel).toHaveBeenCalled();
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
