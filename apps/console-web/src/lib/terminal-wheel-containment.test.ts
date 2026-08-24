import { describe, expect, it, vi } from 'vitest';

import { containTerminalWheelEvent } from './terminal-wheel-containment';

function targetWithClosest(match: boolean): EventTarget {
  return {
    closest: vi.fn(() => (match ? {} : null)),
  } as unknown as EventTarget;
}

describe('terminal wheel containment', () => {
  it('keeps wheel gestures that begin inside xterm from bubbling into IDE panes', () => {
    const stopPropagation = vi.fn();

    expect(
      containTerminalWheelEvent({
        target: targetWithClosest(true),
        stopPropagation,
      }),
    ).toBe(true);
    expect(stopPropagation).toHaveBeenCalledOnce();
  });

  it('leaves non-terminal wheel gestures alone', () => {
    const stopPropagation = vi.fn();

    expect(
      containTerminalWheelEvent({
        target: targetWithClosest(false),
        stopPropagation,
      }),
    ).toBe(false);
    expect(stopPropagation).not.toHaveBeenCalled();
  });
});
