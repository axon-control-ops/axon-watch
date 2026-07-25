import { describe, expect, it, vi } from 'vitest';

import { createOrbTriggerGestureHandlers } from './orb-trigger-gestures';

describe('createOrbTriggerGestureHandlers', () => {
  it('starts long-press watch and voice on pointer down', () => {
    const voice = {
      handleOrbPointerDown: vi.fn(),
      handleOrbPointerUp: vi.fn(),
      cancelOrbPointerGesture: vi.fn(),
    };
    const drag = {
      handleLongPressPointerDown: vi.fn(),
      handleOrbDragMove: vi.fn(),
      finishOrbDrag: vi.fn(() => false),
    };
    const handlers = createOrbTriggerGestureHandlers(voice, drag);
    const event = { pointerId: 1 } as PointerEvent;
    handlers.onTriggerPointerDown(event);
    expect(drag.handleLongPressPointerDown).toHaveBeenCalledWith(event);
    expect(voice.handleOrbPointerDown).toHaveBeenCalledWith(event);
  });

  it('cancels voice when a drag finishes', () => {
    const voice = {
      handleOrbPointerDown: vi.fn(),
      handleOrbPointerUp: vi.fn(),
      cancelOrbPointerGesture: vi.fn(),
    };
    const drag = {
      handleLongPressPointerDown: vi.fn(),
      handleOrbDragMove: vi.fn(),
      finishOrbDrag: vi.fn(() => true),
    };
    const handlers = createOrbTriggerGestureHandlers(voice, drag);
    handlers.onTriggerPointerUp({ pointerId: 1 } as PointerEvent);
    expect(voice.cancelOrbPointerGesture).toHaveBeenCalled();
    expect(voice.handleOrbPointerUp).not.toHaveBeenCalled();
  });
});
