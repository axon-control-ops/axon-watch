import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import {
  enqueueKairoSpeech,
  flushKairoSpeechQueue,
  interruptKairoSpeechQueue,
  isKairoSpeechQueueBusy,
  resetKairoSpeechQueueForTests,
} from './kairo-voice-queue';
import { playKairoUtteranceNow, stopKairoPlayback } from './kairo-voice-playback';

vi.mock('./kairo-voice-playback', () => ({
  playKairoUtteranceNow: vi.fn(),
  stopKairoPlayback: vi.fn().mockResolvedValue(undefined),
}));

describe('kairo voice queue', () => {
  beforeEach(() => {
    resetKairoSpeechQueueForTests();
    vi.mocked(playKairoUtteranceNow).mockReset();
    vi.mocked(stopKairoPlayback).mockClear();
  });

  afterEach(() => {
    flushKairoSpeechQueue('test_teardown');
    resetKairoSpeechQueueForTests();
  });

  it('plays jobs one after another without overlapping', async () => {
    const order: string[] = [];
    vi.mocked(playKairoUtteranceNow).mockImplementation(async (text: string) => {
      order.push(`start:${text}`);
      await Promise.resolve();
      order.push(`end:${text}`);
      return { engine: 'azure', reason: null };
    });

    const first = enqueueKairoSpeech('alpha', { priority: 'narration' });
    const second = enqueueKairoSpeech('bravo', { priority: 'narration' });

    expect(isKairoSpeechQueueBusy()).toBe(true);
    await Promise.all([first, second]);

    expect(order).toEqual([
      'start:alpha',
      'end:alpha',
      'start:bravo',
      'end:bravo',
    ]);
    expect(playKairoUtteranceNow).toHaveBeenCalledTimes(2);
  });

  it('lets alerts jump ahead of waiting narration without cutting active speech', async () => {
    const played: string[] = [];
    const gate = {
      release: null as (() => void) | null,
    };
    vi.mocked(playKairoUtteranceNow).mockImplementation(async (text: string) => {
      played.push(text);
      if (text === 'run update') {
        await new Promise<void>((resolve) => {
          gate.release = resolve;
        });
      }
      return { engine: 'azure', reason: null };
    });

    const narrationA = enqueueKairoSpeech('run update', { priority: 'narration' });
    // Yield so the pump starts the first job before we enqueue more.
    await Promise.resolve();
    await Promise.resolve();

    const narrationB = enqueueKairoSpeech('more run chatter', { priority: 'narration' });
    const alert = enqueueKairoSpeech('signal attention', { priority: 'alert' });

    expect(gate.release).toBeTypeOf('function');
    gate.release?.();

    const results = await Promise.all([narrationA, narrationB, alert]);

    expect(played[0]).toBe('run update');
    expect(played).toContain('signal attention');
    expect(played).not.toContain('more run chatter');
    expect(results[1].engine).toBe('skipped');
    expect(results[1].reason).toBe('preempted_by_alert');
  });

  it('interrupt flushes waiting jobs and stops playback', async () => {
    const gate = {
      release: null as (() => void) | null,
    };
    vi.mocked(playKairoUtteranceNow).mockImplementation(async () => {
      await new Promise<void>((resolve) => {
        gate.release = resolve;
      });
      return { engine: 'azure', reason: null };
    });

    const first = enqueueKairoSpeech('one', { priority: 'conversation' });
    await Promise.resolve();
    await Promise.resolve();
    const second = enqueueKairoSpeech('two', { priority: 'conversation' });

    await interruptKairoSpeechQueue('barge_in');
    expect(stopKairoPlayback).toHaveBeenCalled();

    const secondResult = await second;
    expect(secondResult.engine).toBe('skipped');
    expect(secondResult.reason).toBe('barge_in');

    gate.release?.();
    await first;
  });
});
