import { onBeforeUnmount, onMounted, watch, type Ref } from 'vue';

import {
  applyOrbFieldSampleToElement,
  sampleOrbFieldInfluence,
  type OrbFieldBox,
} from '../lib/orb-field-influence';
import { useShellStore } from '../stores/shell';

const DEFAULT_ORB_BOX = { width: 212, height: 268 };

/**
 * Makes `[data-orb-field]` descendants yield around the floating VAXON orb
 * (push + circular bite mask) while it docks / drags.
 */
export function useOrbFieldReactiveHost(options: {
  root: Ref<HTMLElement | null>;
  selector?: string;
  enabled?: Ref<boolean> | (() => boolean);
}): void {
  const shell = useShellStore();
  const selector = options.selector ?? '[data-orb-field]';
  let frame = 0;
  let ro: ResizeObserver | null = null;

  function isEnabled(): boolean {
    if (!options.enabled) {
      return true;
    }
    return typeof options.enabled === 'function' ? options.enabled() : options.enabled.value;
  }

  function readOrbBox(): OrbFieldBox | null {
    const pos = shell.voiceOrbPosition;
    if (!pos || !shell.voiceOrbVisible || shell.layoutMode === 'ide') {
      return null;
    }
    return {
      x: pos.x,
      y: pos.y,
      width: DEFAULT_ORB_BOX.width,
      height: DEFAULT_ORB_BOX.height,
    };
  }

  function clearAll(root: HTMLElement): void {
    root.querySelectorAll<HTMLElement>(selector).forEach((el) => {
      applyOrbFieldSampleToElement(el, null);
    });
  }

  function tick(): void {
    frame = 0;
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
        maxPush: dragging ? 36 : 24,
        softExtra: dragging ? 48 : 34,
      });
      applyOrbFieldSampleToElement(el, sample);
    });
  }

  function schedule(): void {
    if (frame) {
      return;
    }
    frame = window.requestAnimationFrame(tick);
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
  });

  onBeforeUnmount(() => {
    if (frame) {
      cancelAnimationFrame(frame);
    }
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
      shell.voiceOrbDragging,
      shell.voiceOrbVisible,
      shell.layoutMode,
    ],
    () => schedule(),
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
