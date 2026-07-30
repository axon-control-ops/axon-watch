import { onBeforeUnmount, onMounted, watch, type Ref } from 'vue';

import {
  applyOrbFieldSampleToElement,
  ORB_FIELD_DRAG_MAX_PUSH,
  ORB_FIELD_DRAG_SOFT_EXTRA,
  ORB_FIELD_MAX_PUSH,
  ORB_FIELD_SOFT_EXTRA,
  sampleOrbFieldInfluence,
  type OrbFieldBox,
} from '../lib/orb-field-influence';
import {
  measureVoiceOrbLiveBox,
  voiceOrbBoxFromPosition,
} from '../lib/voice-orb-live-box';
import { useShellStore } from '../stores/shell';

/**
 * Yield `[data-orb-field]` descendants around the live floating orb rect.
 * Continuous rAF while dragging; push clamped inside the host so overflow cannot erase it.
 */
export function useOrbFieldReactiveHost(options: {
  root: Ref<HTMLElement | null>;
  selector?: string;
  enabled?: Ref<boolean> | (() => boolean);
}): void {
  const shell = useShellStore();
  const selector = options.selector ?? '[data-orb-field]';
  let frame = 0;
  let dragLoop = 0;
  let ro: ResizeObserver | null = null;

  function isEnabled(): boolean {
    if (!options.enabled) {
      return true;
    }
    return typeof options.enabled === 'function' ? options.enabled() : options.enabled.value;
  }

  function readOrbBox(): OrbFieldBox | null {
    // Mission Control uses the embedded LIVE OPS orb — never drive card bites from it
    // or from a stale Brain Graph dock position (ghost circle until scroll).
    if (
      !shell.voiceOrbVisible ||
      shell.layoutMode === 'ide' ||
      !shell.operatorBrainGalaxyActive
    ) {
      return null;
    }
    return measureVoiceOrbLiveBox() ?? voiceOrbBoxFromPosition(shell.voiceOrbPosition);
  }

  function clearAll(root: HTMLElement): void {
    root.querySelectorAll<HTMLElement>(selector).forEach((el) => {
      applyOrbFieldSampleToElement(el, null);
    });
  }

  function tick(): void {
    const root = options.root.value;
    if (!root || !isEnabled()) {
      if (root) {
        clearAll(root);
      }
      return;
    }
    const orb = readOrbBox();
    const nodes = root.querySelectorAll<HTMLElement>(selector);
    if (!orb) {
      nodes.forEach((el) => applyOrbFieldSampleToElement(el, null));
      return;
    }
    const dragging = shell.voiceOrbDragging;
    const rootRect = root.getBoundingClientRect();
    const pad = 8;
    nodes.forEach((el) => {
      const rect = el.getBoundingClientRect();
      if (rect.width < 2 || rect.height < 2) {
        applyOrbFieldSampleToElement(el, null);
        return;
      }
      const sample = sampleOrbFieldInfluence({
        orb,
        element: {
          left: rect.left,
          top: rect.top,
          width: rect.width,
          height: rect.height,
        },
        maxPush: dragging ? ORB_FIELD_DRAG_MAX_PUSH : ORB_FIELD_MAX_PUSH,
        softExtra: dragging ? ORB_FIELD_DRAG_SOFT_EXTRA : ORB_FIELD_SOFT_EXTRA,
      });
      if (!sample) {
        applyOrbFieldSampleToElement(el, null);
        return;
      }
      let { pushX, pushY } = sample;
      const nextLeft = rect.left + pushX;
      const nextTop = rect.top + pushY;
      const nextRight = nextLeft + rect.width;
      const nextBottom = nextTop + rect.height;
      if (nextLeft < rootRect.left + pad) {
        pushX += rootRect.left + pad - nextLeft;
      }
      if (nextTop < rootRect.top + pad) {
        pushY += rootRect.top + pad - nextTop;
      }
      if (nextRight > rootRect.right - pad) {
        pushX -= nextRight - (rootRect.right - pad);
      }
      if (nextBottom > rootRect.bottom - pad) {
        pushY -= nextBottom - (rootRect.bottom - pad);
      }
      applyOrbFieldSampleToElement(el, { ...sample, pushX, pushY });
    });
  }

  function schedule(): void {
    if (frame) {
      return;
    }
    frame = window.requestAnimationFrame(() => {
      frame = 0;
      tick();
    });
  }

  function stopDragLoop(): void {
    if (dragLoop) {
      cancelAnimationFrame(dragLoop);
      dragLoop = 0;
    }
  }

  function startDragLoop(): void {
    stopDragLoop();
    const step = (): void => {
      tick();
      if (shell.voiceOrbDragging && isEnabled()) {
        dragLoop = window.requestAnimationFrame(step);
      } else {
        dragLoop = 0;
        schedule();
      }
    };
    dragLoop = window.requestAnimationFrame(step);
  }

  function onScrollOrResize(): void {
    schedule();
  }

  onMounted(() => {
    schedule();
    window.addEventListener('resize', onScrollOrResize, { passive: true });
    window.addEventListener('scroll', onScrollOrResize, { passive: true, capture: true });
    if (typeof ResizeObserver !== 'undefined') {
      ro = new ResizeObserver(() => schedule());
      if (options.root.value) {
        ro.observe(options.root.value);
      }
    }
    if (shell.voiceOrbDragging) {
      startDragLoop();
    }
  });

  onBeforeUnmount(() => {
    if (frame) {
      cancelAnimationFrame(frame);
    }
    stopDragLoop();
    window.removeEventListener('resize', onScrollOrResize);
    window.removeEventListener('scroll', onScrollOrResize, true);
    ro?.disconnect();
    if (options.root.value) {
      clearAll(options.root.value);
    }
  });

  watch(
    () => [
      shell.voiceOrbPosition?.x,
      shell.voiceOrbPosition?.y,
      shell.voiceOrbVisible,
      shell.layoutMode,
      shell.operatorBrainGalaxyActive,
    ],
    () => {
      if (!shell.voiceOrbDragging) {
        schedule();
      }
    },
  );

  watch(
    () => shell.voiceOrbDragging,
    (dragging) => {
      if (dragging) {
        startDragLoop();
      } else {
        stopDragLoop();
        schedule();
      }
    },
  );

  watch(
    () => options.root.value,
    (el, prev) => {
      if (prev && ro) {
        ro.unobserve(prev);
      }
      if (el && ro) {
        ro.observe(el);
      }
      schedule();
    },
  );
}
