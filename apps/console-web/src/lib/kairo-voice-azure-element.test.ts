import { afterEach, describe, expect, it, vi } from 'vitest';

import { playAzureAudioToCompletion } from './kairo-voice-azure-element';

describe('playAzureAudioToCompletion', () => {
  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it('signals audible start after playback begins and encoded silence elapses', async () => {
    vi.useFakeTimers();
    vi.stubGlobal('HTMLMediaElement', {
      HAVE_CURRENT_DATA: 2,
      HAVE_FUTURE_DATA: 3,
      HAVE_ENOUGH_DATA: 4,
    });
    const audio = {
      readyState: 4,
      preload: '',
      muted: false,
      volume: 1,
      onended: null as (() => void) | null,
      onerror: null as (() => void) | null,
      setAttribute: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      play: vi.fn(async () => {
        queueMicrotask(() => audio.onended?.({} as Event));
      }),
    } as unknown as HTMLAudioElement;
    const onAudibleStart = vi.fn();

    const completion = playAzureAudioToCompletion(audio, onAudibleStart, 300);
    await vi.advanceTimersByTimeAsync(160);
    await completion;

    expect(audio.play).toHaveBeenCalledOnce();
    expect(onAudibleStart).not.toHaveBeenCalled();
    await vi.advanceTimersByTimeAsync(579);
    expect(onAudibleStart).not.toHaveBeenCalled();
    await vi.advanceTimersByTimeAsync(1);
    expect(onAudibleStart).toHaveBeenCalledOnce();
  });
});
