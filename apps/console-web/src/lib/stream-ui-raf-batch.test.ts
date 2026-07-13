import { describe, expect, it, vi } from 'vitest';

import { createRafStreamUiBatcher } from './stream-ui-raf-batch';

describe('createRafStreamUiBatcher', () => {
  it('coalesces multiple schedules into one flush per frame', () => {
    const flush = vi.fn();
    const frames: FrameRequestCallback[] = [];
    const batcher = createRafStreamUiBatcher<{ label: string }>(
      (workspaceId, partial) => flush(workspaceId, partial),
      (callback) => {
        frames.push(callback);
        return frames.length;
      },
      () => {},
    );

    batcher.schedule('ws_1', { label: 'first' });
    batcher.schedule('ws_1', { label: 'second' });
    expect(flush).not.toHaveBeenCalled();

    frames[0](0);
    expect(flush).toHaveBeenCalledTimes(1);
    expect(flush).toHaveBeenCalledWith('ws_1', { label: 'second' });
  });

  it('flushes pending updates immediately on flushNow', () => {
    const flush = vi.fn();
    const batcher = createRafStreamUiBatcher<{ label: string }>(
      (workspaceId, partial) => flush(workspaceId, partial),
      () => 1,
      () => {},
    );

    batcher.schedule('ws_1', { label: 'pending' });
    batcher.flushNow('ws_1');
    expect(flush).toHaveBeenCalledWith('ws_1', { label: 'pending' });
  });
});
