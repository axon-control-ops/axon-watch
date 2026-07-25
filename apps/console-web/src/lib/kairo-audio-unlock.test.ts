import { afterEach, describe, expect, it, vi } from 'vitest';

import {
  isDesktopWebView,
  isKairoAudioUnlocked,
  isKairoMediaUnlocked,
  resetKairoAudioUnlockState,
  unlockKairoAudioPlayback,
} from './kairo-audio-unlock';

describe('kairo-audio-unlock', () => {
  afterEach(() => {
    resetKairoAudioUnlockState();
    vi.unstubAllGlobals();
  });

  it('detects Tauri 2 via __TAURI_INTERNALS__', () => {
    vi.stubGlobal('window', {
      __TAURI_INTERNALS__: {},
    });
    expect(isDesktopWebView()).toBe(true);
  });

  it('unlocks AudioContext and HTMLAudioElement playback', async () => {
    class FakeAudioContext {
      state = 'running';
      resume = vi.fn(async () => undefined);
      createBuffer = vi.fn(() => ({}));
      createBufferSource = vi.fn(() => ({
        buffer: null as unknown,
        connect: vi.fn(),
        start: vi.fn(),
      }));
      destination = {};
      close = vi.fn(async () => undefined);
    }

    class FakeAudio {
      volume = 1;
      src = '';
      setAttribute = vi.fn();
      play = vi.fn(async () => undefined);
      pause = vi.fn();
      constructor(src: string) {
        this.src = src;
      }
    }

    vi.stubGlobal('window', {
      AudioContext: FakeAudioContext,
      Audio: FakeAudio,
    });
    vi.stubGlobal('Audio', FakeAudio);
    vi.stubGlobal('AudioContext', FakeAudioContext);

    const ok = await unlockKairoAudioPlayback();
    expect(ok).toBe(true);
    expect(isKairoAudioUnlocked()).toBe(true);
    expect(isKairoMediaUnlocked()).toBe(true);
  });
});
