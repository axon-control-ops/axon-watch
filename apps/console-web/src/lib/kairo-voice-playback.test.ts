import { afterEach, describe, expect, it, vi } from 'vitest';

import { postKairoTts } from './kairo-tts-client';
import { resetSpeechQueue } from './speech-queue';
import { speakKairoLine, stopKairoPlayback } from './kairo-voice-playback';

vi.mock('./kairo-tts-client', () => ({
  postKairoTts: vi.fn(),
}));

function stubBrowserSpeech() {
  class MockSpeechSynthesisUtterance {
    message: string;
    rate = 1;
    onend: (() => void) | null = null;
    onerror: (() => void) | null = null;

    constructor(message: string) {
      this.message = message;
    }
  }

  vi.stubGlobal('SpeechSynthesisUtterance', MockSpeechSynthesisUtterance);
  const speech = {
    speak: vi.fn((utterance: MockSpeechSynthesisUtterance) => {
      globalThis.setTimeout(() => utterance.onend?.(), 0);
    }),
    getVoices: vi.fn().mockReturnValue([]),
    cancel: vi.fn(),
  };
  vi.stubGlobal('speechSynthesis', speech);
  return speech;
}

describe('kairo voice playback', () => {
  afterEach(() => {
    stopKairoPlayback();
    resetSpeechQueue();
    vi.mocked(postKairoTts).mockReset();
    vi.unstubAllGlobals();
  });

  it('falls back to browser speech when azure is unavailable', async () => {
    vi.useFakeTimers();
    const speech = stubBrowserSpeech();
    vi.mocked(postKairoTts).mockResolvedValue({
      available: false,
      provider: 'browser',
      reason: 'synthesis_failed',
    });

    const promise = speakKairoLine('Hello operator', { immediate: true });
    await vi.advanceTimersByTimeAsync(800);
    const result = await promise;

    expect(result.engine).toBe('browser');
    expect(result.reason).toBe('synthesis_failed');
    expect(speech.speak).toHaveBeenCalledOnce();

    vi.useRealTimers();
  });

  it('does not re-speak azure audio when a later chunk falls back to browser', async () => {
    vi.useFakeTimers();
    const speech = stubBrowserSpeech();

    const firstChunk =
      `${'Alpha sentence one. '.repeat(40)}Alpha sentence two.`.trim();
    const secondChunk =
      `${'Bravo sentence one. '.repeat(40)}Bravo sentence two.`.trim();
    const longText = `${firstChunk} ${secondChunk}`;

    class FakeAudio {
      static instances: FakeAudio[] = [];
      src = '';
      preload = '';
      currentTime = 0;
      readyState = 2;
      paused = true;
      ended = false;
      onended: (() => void) | null = null;
      onerror: (() => void) | null = null;

      constructor(src: string) {
        this.src = src;
        FakeAudio.instances.push(this);
      }

      addEventListener(): void {}
      removeEventListener(): void {}
      load(): void {}
      pause(): void {
        this.paused = true;
      }
      play(): Promise<void> {
        this.paused = false;
        globalThis.setTimeout(() => {
          this.ended = true;
          this.paused = true;
          this.onended?.();
        }, 0);
        return Promise.resolve();
      }
    }

    FakeAudio.instances = [];
    vi.stubGlobal('Audio', FakeAudio as unknown as typeof Audio);
    vi.stubGlobal('HTMLMediaElement', {
      HAVE_CURRENT_DATA: 2,
      HAVE_ENOUGH_DATA: 4,
      NETWORK_EMPTY: 0,
    });
    vi.stubGlobal('URL', {
      ...URL,
      createObjectURL: vi.fn(() => 'blob:fake-azure-audio'),
      revokeObjectURL: vi.fn(),
    });

    vi.mocked(postKairoTts)
      .mockResolvedValueOnce({
        available: true,
        provider: 'azure',
        audio_base64: 'YQ==',
        content_type: 'audio/mpeg',
      })
      .mockResolvedValueOnce({
        available: false,
        provider: 'browser',
        reason: 'synthesis_failed',
      });

    const promise = speakKairoLine(longText, { immediate: true });
    await vi.advanceTimersByTimeAsync(800);
    const result = await promise;

    expect(result.engine).toBe('browser');
    expect(result.reason).toBe('synthesis_failed');
    expect(FakeAudio.instances).toHaveLength(1);
    expect(FakeAudio.instances[0]?.src).toBe('blob:fake-azure-audio');
    expect(speech.speak).toHaveBeenCalled();

    const spoken = speech.speak.mock.calls
      .map((call) => String((call[0] as { message?: string }).message || ''))
      .join(' ');
    expect(spoken).toContain('Bravo');
    expect(spoken).not.toContain('Alpha');

    vi.useRealTimers();
  });

  it('plays azure audio when preload events never fire', async () => {
    vi.useFakeTimers();
    stubBrowserSpeech();

    class StuckPreloadAudio {
      src = '';
      preload = '';
      currentTime = 0;
      readyState = 0;
      paused = true;
      ended = false;
      onended: (() => void) | null = null;
      onerror: (() => void) | null = null;
      loadCalls = 0;

      constructor(src: string) {
        this.src = src;
      }

      addEventListener(): void {}
      removeEventListener(): void {}
      load(): void {
        this.loadCalls += 1;
      }
      pause(): void {
        this.paused = true;
      }
      play(): Promise<void> {
        this.paused = false;
        this.readyState = 4;
        globalThis.setTimeout(() => {
          this.ended = true;
          this.paused = true;
          this.onended?.();
        }, 0);
        return Promise.resolve();
      }
    }

    const audio = { current: null as StuckPreloadAudio | null };
    vi.stubGlobal(
      'Audio',
      class {
        constructor(src: string) {
          audio.current = new StuckPreloadAudio(src);
          return audio.current;
        }
      } as unknown as typeof Audio,
    );
    vi.stubGlobal('HTMLMediaElement', {
      HAVE_CURRENT_DATA: 2,
      HAVE_ENOUGH_DATA: 4,
      NETWORK_EMPTY: 0,
    });
    vi.stubGlobal('URL', {
      ...URL,
      createObjectURL: vi.fn(() => 'blob:stuck-preload'),
      revokeObjectURL: vi.fn(),
    });

    vi.mocked(postKairoTts).mockResolvedValue({
      available: true,
      provider: 'azure',
      audio_base64: 'YQ==',
      content_type: 'audio/mpeg',
    });

    const promise = speakKairoLine('Systems nominal.', { immediate: true });
    await vi.advanceTimersByTimeAsync(3000);
    const result = await promise;

    expect(result.engine).toBe('azure');
    expect(audio.current?.loadCalls).toBe(0);
    expect(audio.current?.src).toBe('blob:stuck-preload');

    vi.useRealTimers();
  });
});
