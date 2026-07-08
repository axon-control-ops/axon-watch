import { afterEach, describe, expect, it, vi } from 'vitest';

import { postKairoTts } from './kairo-tts-client';
import { resetSpeechQueue } from './speech-queue';
import { speakKairoLine, stopKairoPlayback } from './kairo-voice-playback';

vi.mock('./kairo-tts-client', () => ({
  postKairoTts: vi.fn(),
}));

describe('kairo voice playback', () => {
  afterEach(() => {
    stopKairoPlayback();
    resetSpeechQueue();
    vi.mocked(postKairoTts).mockReset();
  });

  it('falls back to browser speech when azure is unavailable', async () => {
    vi.useFakeTimers();

    class MockSpeechSynthesisUtterance {
      message: string;
      rate = 1;

      constructor(message: string) {
        this.message = message;
      }
    }

    vi.stubGlobal('SpeechSynthesisUtterance', MockSpeechSynthesisUtterance);
    const speech = { speak: vi.fn(), getVoices: vi.fn().mockReturnValue([]) };
    vi.stubGlobal('speechSynthesis', speech);
    vi.mocked(postKairoTts).mockResolvedValue({
      available: false,
      provider: 'browser',
      reason: 'synthesis_failed',
    });

    const promise = speakKairoLine('Hello operator');
    await vi.advanceTimersByTimeAsync(200);
    const result = await promise;

    expect(result.engine).toBe('browser');
    expect(result.reason).toBe('synthesis_failed');
    expect(speech.speak).toHaveBeenCalledOnce();

    vi.useRealTimers();
  });
});
