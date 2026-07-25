export type OrbTriggerVoiceHandlers = {
  handleOrbPointerDown: (event: PointerEvent) => void;
  handleOrbPointerUp: (event: PointerEvent) => void;
  cancelOrbPointerGesture: () => void;
};

export type OrbTriggerDragHandlers = {
  handleLongPressPointerDown: (event: PointerEvent) => void;
  handleOrbDragMove: (event: PointerEvent) => void;
  finishOrbDrag: (event: PointerEvent) => boolean;
};

/** Wire hold-to-talk with long-press-to-move on the same orb trigger. */
export function createOrbTriggerGestureHandlers(
  voice: OrbTriggerVoiceHandlers,
  drag: OrbTriggerDragHandlers,
): {
  onTriggerPointerDown: (event: PointerEvent) => void;
  onTriggerPointerMove: (event: PointerEvent) => void;
  onTriggerPointerUp: (event: PointerEvent) => void;
} {
  return {
    onTriggerPointerDown(event: PointerEvent): void {
      drag.handleLongPressPointerDown(event);
      voice.handleOrbPointerDown(event);
    },
    onTriggerPointerMove(event: PointerEvent): void {
      drag.handleOrbDragMove(event);
    },
    onTriggerPointerUp(event: PointerEvent): void {
      const dragged = drag.finishOrbDrag(event);
      if (dragged) {
        voice.cancelOrbPointerGesture();
        return;
      }
      voice.handleOrbPointerUp(event);
    },
  };
}
