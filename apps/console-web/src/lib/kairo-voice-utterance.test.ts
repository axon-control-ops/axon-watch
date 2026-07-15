import { describe, expect, it, beforeEach } from 'vitest';

import {
  getKairoVoiceUtterance,
  notifyKairoVoiceUtterance,
  resetKairoVoiceUtteranceForTests,
  subscribeKairoVoiceUtterance,
} from './kairo-voice-utterance';

describe('kairo-voice-utterance', () => {
  beforeEach(() => {
    resetKairoVoiceUtteranceForTests();
  });

  it('notifies subscribers when utterance text starts and ends', () => {
    const seen: Array<string | null> = [];
    const unsubscribe = subscribeKairoVoiceUtterance((text) => {
      seen.push(text);
    });

    notifyKairoVoiceUtterance('Systems nominal.');
    notifyKairoVoiceUtterance('Systems nominal.');
    notifyKairoVoiceUtterance(null);

    expect(getKairoVoiceUtterance()).toBeNull();
    expect(seen).toEqual([null, 'Systems nominal.', null]);
    unsubscribe();
  });
});
