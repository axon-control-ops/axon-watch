import { afterEach, describe, expect, it, vi } from 'vitest';

import {
  isKairoPlaybackActive,
  isKairoPlaybackPaused,
  pauseKairoPlayback,
  resumeKairoPlayback,
  stopKairoPlayback,
} from './kairo-playback-control';
import { resetSpeechQueue } from './speech-queue';

describe('kairo playback control', () => {
  afterEach(() => {
    stopKairoPlayback();
    resetSpeechQueue();
  });

  it('pauses and resumes browser speech synthesis', () => {
    const speech = {
      speaking: true,
      paused: false,
      speak: vi.fn(),
      getVoices: vi.fn().mockReturnValue([]),
      pause: vi.fn(function pause(this: { paused: boolean }) {
        this.paused = true;
      }),
      resume: vi.fn(function resume(this: { paused: boolean }) {
        this.paused = false;
      }),
      cancel: vi.fn(),
    };

    vi.stubGlobal('speechSynthesis', speech);

    expect(pauseKairoPlayback()).toBe(true);
    expect(isKairoPlaybackPaused()).toBe(true);
    expect(isKairoPlaybackActive()).toBe(true);

    expect(resumeKairoPlayback()).toBe(true);
    expect(isKairoPlaybackPaused()).toBe(false);
  });
});
