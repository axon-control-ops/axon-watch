import { describe, expect, it, beforeEach } from 'vitest';

import {
  getKairoVoiceSpeaker,
  getKairoVoiceUtterance,
  notifyKairoVoiceUtterance,
  resetKairoVoiceUtteranceForTests,
  subscribeKairoVoiceUtterance,
  vaxonVoiceSpeaker,
} from './kairo-voice-utterance';

describe('kairo-voice-utterance', () => {
  beforeEach(() => {
    resetKairoVoiceUtteranceForTests();
  });

  it('notifies subscribers when utterance text starts and ends', () => {
    const seen: Array<string | null> = [];
    const unsubscribe = subscribeKairoVoiceUtterance((state) => {
      seen.push(state.text);
    });

    notifyKairoVoiceUtterance('Systems nominal.', vaxonVoiceSpeaker());
    notifyKairoVoiceUtterance('Systems nominal.', vaxonVoiceSpeaker());
    notifyKairoVoiceUtterance(null);

    expect(getKairoVoiceUtterance()).toBeNull();
    expect(getKairoVoiceSpeaker()).toBeNull();
    expect(seen).toEqual([null, 'Systems nominal.', null]);
    unsubscribe();
  });

  it('keeps speaker identity with the active utterance', () => {
    notifyKairoVoiceUtterance('Heads up.', vaxonVoiceSpeaker());
    expect(getKairoVoiceSpeaker()?.kind).toBe('vaxon');
    expect(getKairoVoiceSpeaker()?.name).toBe('VAXON');
  });
});
