import { nextTick, onBeforeUnmount, onMounted, ref, type Ref, watch } from 'vue';

import {
  clampPlacementToViewport,
  collectObstacleRects,
  DEFAULT_VOICE_ORB_DOCK,
  placementOverlapsObstacles,
  resolvePlacementForDock,
  resolveSmartDodgePlacement,
  VOICE_ORB_VIEWPORT_MARGINS,
} from './voice-orb-placement';

/** Hold duration before the orb enters drag/move mode. */
export const ORB_LONG_PRESS_MOVE_MS = 480;
const ORB_LONG_PRESS_MOVE_SLOP_PX = 10;

export type VoiceOrbPlacementApi = {
  voiceOrbPosition: Ref<{ x: number; y: number } | null>;
  voiceOrbUserPinned: Ref<boolean>;
  voiceOrbDragging: Ref<boolean>;
  voiceOrbAnchorStyle: Ref<Record<string, string> | undefined>;
  setVoiceOrbDock: (dock: string) => void;
  setVoiceOrbPosition: (
    position: { x: number; y: number },
    options?: { pin?: boolean; persist?: boolean },
  ) => void;
  resetVoiceOrbDock: () => void;
  requestVoiceOrbSmartDodge: (options?: { force?: boolean }) => void;
  ensureVoiceOrbPosition: (orbAnchor: HTMLElement | null) => { x: number; y: number };
  persistVoiceOrbPlacement: () => void;
};

export type UseKairoGalaxyOrbDragOptions = {
  orbAnchor: Ref<HTMLElement | null>;
  /** When reply HUD content changes, re-check overlap. */
  replySignal: Ref<unknown>;
  /** When set, use viewport/shell placement instead of stage-local drag. */
  placement?: VoiceOrbPlacementApi;
  /** embedded = mobile relative layout (no fixed reposition). */
  mode?: 'viewport' | 'embedded';
  /** Fired when long-press engages drag (cancel voice PTT / click). */
  onDragEngaged?: () => void;
};

export function useKairoGalaxyOrbDrag(options: UseKairoGalaxyOrbDragOptions) {
  const mode = options.mode ?? (options.placement ? 'viewport' : 'embedded');
  const placement = options.placement;

  const orbDragging = placement?.voiceOrbDragging ?? ref(false);
  const orbAnchorStyle =
    placement?.voiceOrbAnchorStyle ?? ref<Record<string, string> | undefined>(undefined);

  let dragPointerId: number | null = null;
  let dragOrigin: { x: number; y: number } | null = null;
  let dragStartPointer: { x: number; y: number } | null = null;
  let longPressTimer: ReturnType<typeof setTimeout> | null = null;
  let longPressPointerId: number | null = null;
  let longPressOrigin: { x: number; y: number } | null = null;
  let longPressLast: { x: number; y: number } | null = null;
  let longPressTarget: HTMLElement | null = null;
  let dodgeTimer: ReturnType<typeof setTimeout> | null = null;
  let dodgeRunning = false;

  function viewportSize() {
    return {
      width: typeof window !== 'undefined' ? window.innerWidth : 1280,
      height: typeof window !== 'undefined' ? window.innerHeight : 800,
    };
  }

  function orbSize() {
    const anchor = options.orbAnchor.value;
    return {
      width: anchor?.offsetWidth || 212,
      height: anchor?.offsetHeight || 268,
    };
  }

  function syncViewportStyle(): void {
    if (!placement) {
      return;
    }
    placement.ensureVoiceOrbPosition(options.orbAnchor.value);
  }

  function clearLongPressTimer(): void {
    if (longPressTimer !== null) {
      clearTimeout(longPressTimer);
      longPressTimer = null;
    }
    longPressPointerId = null;
    longPressOrigin = null;
    longPressLast = null;
    longPressTarget = null;
  }

  function runSmartDodgeNow(): void {
    if (!placement || mode !== 'viewport' || dodgeRunning) {
      return;
    }
    if (placement.voiceOrbUserPinned.value || orbDragging.value) {
      return;
    }
    dodgeRunning = true;
    try {
      const viewport = viewportSize();
      const orb = orbSize();
      const obstacles = collectObstacleRects(typeof document !== 'undefined' ? document : null);
      const current = placement.voiceOrbPosition.value;
      if (current && !placementOverlapsObstacles(current, orb, obstacles)) {
        return;
      }
      const result = resolveSmartDodgePlacement({
        viewport,
        orb,
        obstacles,
        preferredDock: DEFAULT_VOICE_ORB_DOCK,
      });
      if (
        current &&
        Math.abs(current.x - result.position.x) < 1 &&
        Math.abs(current.y - result.position.y) < 1
      ) {
        return;
      }
      placement.setVoiceOrbDock(result.dock);
    } finally {
      dodgeRunning = false;
    }
  }

  function scheduleSmartDodge(): void {
    if (!placement || mode !== 'viewport') {
      return;
    }
    if (dodgeTimer !== null) {
      clearTimeout(dodgeTimer);
    }
    dodgeTimer = setTimeout(() => {
      dodgeTimer = null;
      void nextTick(() => {
        runSmartDodgeNow();
      });
    }, 120);
  }

  function engageDragFromLongPress(
    pointerId: number,
    target: HTMLElement,
    pointer: { x: number; y: number },
  ): void {
    if (mode === 'embedded' || !placement) {
      return;
    }
    const current = placement.ensureVoiceOrbPosition(options.orbAnchor.value);
    target.setPointerCapture?.(pointerId);
    dragPointerId = pointerId;
    dragOrigin = { ...current };
    dragStartPointer = { ...pointer };
    orbDragging.value = true;
    options.onDragEngaged?.();
  }

  function handleLongPressPointerDown(event: PointerEvent): void {
    if (mode === 'embedded' || !placement) {
      return;
    }
    if (event.button !== 0 && event.pointerType === 'mouse') {
      return;
    }
    const target = event.currentTarget;
    if (!(target instanceof HTMLElement)) {
      return;
    }
    clearLongPressTimer();
    longPressPointerId = event.pointerId;
    longPressOrigin = { x: event.clientX, y: event.clientY };
    longPressLast = { x: event.clientX, y: event.clientY };
    longPressTarget = target;
    const armedPointerId = event.pointerId;
    longPressTimer = setTimeout(() => {
      longPressTimer = null;
      if (longPressPointerId !== armedPointerId || !longPressTarget || !longPressLast) {
        return;
      }
      const targetEl = longPressTarget;
      const pointer = { ...longPressLast };
      longPressPointerId = null;
      longPressOrigin = null;
      longPressLast = null;
      longPressTarget = null;
      engageDragFromLongPress(armedPointerId, targetEl, pointer);
    }, ORB_LONG_PRESS_MOVE_MS);
  }

  function handleOrbDragMove(event: PointerEvent): void {
    if (mode === 'embedded' || !placement) {
      return;
    }

    if (
      longPressTimer !== null &&
      longPressPointerId === event.pointerId &&
      longPressOrigin
    ) {
      longPressLast = { x: event.clientX, y: event.clientY };
      const dx = event.clientX - longPressOrigin.x;
      const dy = event.clientY - longPressOrigin.y;
      if (Math.hypot(dx, dy) > ORB_LONG_PRESS_MOVE_SLOP_PX) {
        clearLongPressTimer();
      }
    }

    if (
      dragPointerId === null ||
      event.pointerId !== dragPointerId ||
      !dragOrigin ||
      !dragStartPointer
    ) {
      return;
    }
    event.preventDefault();
    const next = clampPlacementToViewport({
      position: {
        x: dragOrigin.x + (event.clientX - dragStartPointer.x),
        y: dragOrigin.y + (event.clientY - dragStartPointer.y),
      },
      viewport: viewportSize(),
      orb: orbSize(),
      margins: VOICE_ORB_VIEWPORT_MARGINS,
    });
    placement.setVoiceOrbPosition(next, { pin: false, persist: false });
  }

  function finishOrbDrag(event: PointerEvent): boolean {
    clearLongPressTimer();
    if (mode === 'embedded' || !placement) {
      return false;
    }
    const wasDragging = orbDragging.value && dragPointerId === event.pointerId;
    const target = event.currentTarget;
    if (target instanceof HTMLElement && dragPointerId !== null) {
      try {
        if (target.hasPointerCapture?.(dragPointerId)) {
          target.releasePointerCapture(dragPointerId);
        }
      } catch {
        // ignore
      }
    }
    if (dragPointerId === null) {
      return false;
    }
    if (event.pointerId !== dragPointerId) {
      return wasDragging;
    }
    dragPointerId = null;
    dragOrigin = null;
    dragStartPointer = null;
    orbDragging.value = false;
    if (wasDragging && placement.voiceOrbPosition.value) {
      placement.setVoiceOrbPosition(placement.voiceOrbPosition.value, { pin: true });
    }
    return wasDragging;
  }

  function resetOrbPosition(): void {
    if (!placement || mode === 'embedded') {
      return;
    }
    placement.resetVoiceOrbDock();
  }

  function handleWindowResize(): void {
    if (!placement || mode !== 'viewport') {
      return;
    }
    syncViewportStyle();
    scheduleSmartDodge();
  }

  onMounted(() => {
    if (mode !== 'viewport' || !placement) {
      return;
    }
    window.requestAnimationFrame(() => {
      syncViewportStyle();
      scheduleSmartDodge();
    });
    window.addEventListener('resize', handleWindowResize);
  });

  watch(options.replySignal, () => {
    scheduleSmartDodge();
  });

  onBeforeUnmount(() => {
    clearLongPressTimer();
    if (dodgeTimer !== null) {
      clearTimeout(dodgeTimer);
      dodgeTimer = null;
    }
    if (mode === 'viewport') {
      window.removeEventListener('resize', handleWindowResize);
    }
  });

  return {
    orbDragging,
    orbAnchorStyle,
    resolveOrbOverlap: scheduleSmartDodge,
    handleLongPressPointerDown,
    handleOrbDragMove,
    finishOrbDrag,
    resetOrbPosition,
    resolveDefaultDockPosition: () =>
      resolvePlacementForDock({
        dock: DEFAULT_VOICE_ORB_DOCK,
        viewport: viewportSize(),
        orb: orbSize(),
      }),
  };
}
