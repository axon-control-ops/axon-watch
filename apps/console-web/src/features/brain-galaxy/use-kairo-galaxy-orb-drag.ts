import { nextTick, onBeforeUnmount, onMounted, ref, type Ref, watch } from 'vue';

import { rectsOverlap, resolveAutoAvoidOrbCandidates } from './kairo-galaxy-orb-position';

const ORB_DRAG_STORAGE_KEY = 'axon-x:vaxon-orb-position';
const ORB_MARGIN_LEFT_PX = 12;
const ORB_MARGIN_TOP_PX = 56;
const ORB_MARGIN_RIGHT_PX = 12;
const ORB_MARGIN_BOTTOM_PX = 94;
const ORB_REPLY_CLEARANCE_PX = 12;
const ORB_TOP_DOCK_OFFSET_PX = 48;

export type UseKairoGalaxyOrbDragOptions = {
  orbAnchor: Ref<HTMLElement | null>;
  /** When reply HUD content changes, re-check overlap. */
  replySignal: Ref<unknown>;
};

export function useKairoGalaxyOrbDrag(options: UseKairoGalaxyOrbDragOptions) {
  const orbPosition = ref<{ x: number; y: number } | null>(null);
  const orbDragging = ref(false);
  let orbUserPositioned = false;
  let orbAutoAvoidActive = false;
  let dragPointerId: number | null = null;
  let dragOrigin: { x: number; y: number } | null = null;
  let dragStartPointer: { x: number; y: number } | null = null;
  let bottomHudObserver: ResizeObserver | null = null;

  const orbAnchorStyle = ref<Record<string, string> | undefined>(undefined);

  function stageElement(): HTMLElement | null {
    return options.orbAnchor.value?.closest('.brain-galaxy-stage') as HTMLElement | null;
  }

  function bottomHudElement(): HTMLElement | null {
    return stageElement()?.querySelector('.brain-galaxy-stage__hud--bottom') ?? null;
  }

  function orbOverlapsBottomHud(): boolean {
    const anchor = options.orbAnchor.value;
    const hud = bottomHudElement();
    if (!anchor || !hud) {
      return false;
    }
    return rectsOverlap(anchor.getBoundingClientRect(), hud.getBoundingClientRect());
  }

  function clampOrbPosition(position: { x: number; y: number }): { x: number; y: number } {
    const stage = stageElement();
    const anchor = options.orbAnchor.value;
    if (!stage || !anchor) {
      return position;
    }
    const maxX = Math.max(
      ORB_MARGIN_LEFT_PX,
      stage.clientWidth - anchor.offsetWidth - ORB_MARGIN_RIGHT_PX,
    );
    const maxY = Math.max(
      ORB_MARGIN_TOP_PX,
      stage.clientHeight - anchor.offsetHeight - ORB_MARGIN_BOTTOM_PX,
    );
    return {
      x: Math.min(Math.max(position.x, ORB_MARGIN_LEFT_PX), maxX),
      y: Math.min(Math.max(position.y, ORB_MARGIN_TOP_PX), maxY),
    };
  }

  function persistOrbPosition(): void {
    if (!orbPosition.value || typeof localStorage === 'undefined') {
      return;
    }
    localStorage.setItem(ORB_DRAG_STORAGE_KEY, JSON.stringify(orbPosition.value));
  }

  function restoreOrbPosition(): { x: number; y: number } | null {
    if (typeof localStorage === 'undefined') {
      return null;
    }
    try {
      const raw = localStorage.getItem(ORB_DRAG_STORAGE_KEY);
      if (!raw) {
        return null;
      }
      const parsed = JSON.parse(raw) as { x?: unknown; y?: unknown };
      if (typeof parsed.x === 'number' && typeof parsed.y === 'number') {
        return { x: parsed.x, y: parsed.y };
      }
    } catch {
      // Ignore malformed saved positions.
    }
    return null;
  }

  function defaultOrbPosition(): { x: number; y: number } | null {
    const stage = stageElement();
    const anchor = options.orbAnchor.value;
    if (!stage || !anchor) {
      return null;
    }
    return clampOrbPosition({
      x: stage.clientWidth - anchor.offsetWidth - ORB_MARGIN_RIGHT_PX,
      y: ORB_MARGIN_TOP_PX + ORB_TOP_DOCK_OFFSET_PX,
    });
  }

  function syncAnchorStyle(): void {
    if (!orbPosition.value) {
      orbAnchorStyle.value = undefined;
      return;
    }
    orbAnchorStyle.value = {
      left: `${orbPosition.value.x}px`,
      top: `${orbPosition.value.y}px`,
    };
  }

  function applyOrbReplyAvoidPosition(): void {
    const stage = stageElement();
    const anchor = options.orbAnchor.value;
    const hud = bottomHudElement();
    if (!stage || !anchor || !hud) {
      return;
    }
    const stageRect = stage.getBoundingClientRect();
    const hudRect = hud.getBoundingClientRect();
    const candidates = resolveAutoAvoidOrbCandidates({
      stage: { width: stage.clientWidth, height: stage.clientHeight },
      orb: { width: anchor.offsetWidth, height: anchor.offsetHeight },
      obstacle: {
        left: hudRect.left - stageRect.left,
        top: hudRect.top - stageRect.top,
        right: hudRect.right - stageRect.left,
        bottom: hudRect.bottom - stageRect.top,
      },
      margins: {
        left: ORB_MARGIN_LEFT_PX,
        top: ORB_MARGIN_TOP_PX,
        right: ORB_MARGIN_RIGHT_PX,
        bottom: ORB_MARGIN_BOTTOM_PX,
      },
      dockTopOffset: ORB_TOP_DOCK_OFFSET_PX,
      clearance: ORB_REPLY_CLEARANCE_PX,
    });
    for (const candidate of candidates) {
      orbPosition.value = clampOrbPosition(candidate);
      syncAnchorStyle();
      if (!orbOverlapsBottomHud()) {
        orbAutoAvoidActive = true;
        return;
      }
    }
    orbAutoAvoidActive = true;
  }

  function resolveOrbOverlap(): void {
    if (orbDragging.value || orbUserPositioned) {
      return;
    }
    void nextTick(() => {
      if (orbDragging.value || orbUserPositioned) {
        return;
      }
      if (orbOverlapsBottomHud()) {
        applyOrbReplyAvoidPosition();
        return;
      }
      if (orbAutoAvoidActive) {
        orbAutoAvoidActive = false;
        syncOrbPosition(true);
      }
    });
  }

  function attachBottomHudObserver(): void {
    bottomHudObserver?.disconnect();
    const hud = bottomHudElement();
    if (!hud || typeof ResizeObserver === 'undefined') {
      return;
    }
    bottomHudObserver = new ResizeObserver(() => {
      resolveOrbOverlap();
    });
    bottomHudObserver.observe(hud);
  }

  function syncOrbPosition(initial = false): void {
    const base = (initial ? restoreOrbPosition() : orbPosition.value) ?? defaultOrbPosition();
    if (!base) {
      return;
    }
    orbPosition.value = clampOrbPosition(base);
    syncAnchorStyle();
  }

  function handleWindowResize(): void {
    syncOrbPosition();
    resolveOrbOverlap();
  }

  function handleOrbDragStart(event: PointerEvent): void {
    const target = event.currentTarget;
    if (!(target instanceof HTMLElement)) {
      return;
    }
    if (orbPosition.value === null) {
      syncOrbPosition(true);
    }
    target.setPointerCapture?.(event.pointerId);
    dragPointerId = event.pointerId;
    dragOrigin = orbPosition.value ? { ...orbPosition.value } : defaultOrbPosition();
    dragStartPointer = { x: event.clientX, y: event.clientY };
    orbDragging.value = true;
  }

  function handleOrbDragMove(event: PointerEvent): void {
    if (
      dragPointerId === null ||
      event.pointerId !== dragPointerId ||
      !dragOrigin ||
      !dragStartPointer
    ) {
      return;
    }
    orbPosition.value = clampOrbPosition({
      x: dragOrigin.x + (event.clientX - dragStartPointer.x),
      y: dragOrigin.y + (event.clientY - dragStartPointer.y),
    });
    syncAnchorStyle();
  }

  function finishOrbDrag(event: PointerEvent): void {
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
      return;
    }
    dragPointerId = null;
    dragOrigin = null;
    dragStartPointer = null;
    orbDragging.value = false;
    orbUserPositioned = true;
    persistOrbPosition();
  }

  function resetOrbPosition(): void {
    orbUserPositioned = false;
    orbAutoAvoidActive = false;
    const next = defaultOrbPosition();
    if (!next) {
      return;
    }
    orbPosition.value = next;
    persistOrbPosition();
    syncAnchorStyle();
  }

  onMounted(() => {
    window.requestAnimationFrame(() => {
      syncOrbPosition(true);
      attachBottomHudObserver();
      resolveOrbOverlap();
    });
    window.addEventListener('resize', handleWindowResize);
  });

  watch(options.replySignal, () => {
    resolveOrbOverlap();
  });

  onBeforeUnmount(() => {
    bottomHudObserver?.disconnect();
    bottomHudObserver = null;
    window.removeEventListener('resize', handleWindowResize);
  });

  return {
    orbDragging,
    orbAnchorStyle,
    resolveOrbOverlap,
    handleOrbDragStart,
    handleOrbDragMove,
    finishOrbDrag,
    resetOrbPosition,
  };
}
