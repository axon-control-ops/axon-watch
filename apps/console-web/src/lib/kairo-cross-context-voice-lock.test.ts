import { afterEach, describe, expect, it, vi } from 'vitest';

import {
  resetKairoCrossContextVoiceLockForTests,
  withKairoCrossContextVoiceLock,
} from './kairo-cross-context-voice-lock';

describe('kairo-cross-context-voice-lock', () => {
  afterEach(() => {
    resetKairoCrossContextVoiceLockForTests();
  });

  it('skips work when the document is hidden', async () => {
    const work = vi.fn(async () => 'ran');
    const locked = await withKairoCrossContextVoiceLock(work, {
      isHidden: () => true,
    });
    expect(locked).toEqual({ ran: false, result: null });
    expect(work).not.toHaveBeenCalled();
  });

  it('serializes overlapping work across waiters', async () => {
    const order: string[] = [];
    const first = withKairoCrossContextVoiceLock(async () => {
      order.push('first-start');
      await new Promise((resolve) => globalThis.setTimeout(resolve, 80));
      order.push('first-end');
      return 'first';
    });
    await new Promise((resolve) => globalThis.setTimeout(resolve, 10));
    const second = withKairoCrossContextVoiceLock(async () => {
      order.push('second-start');
      order.push('second-end');
      return 'second';
    });

    const [a, b] = await Promise.all([first, second]);
    expect(a).toEqual({ ran: true, result: 'first' });
    expect(b).toEqual({ ran: true, result: 'second' });
    expect(order).toEqual(['first-start', 'first-end', 'second-start', 'second-end']);
  });
});
