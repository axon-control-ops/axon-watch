import type { OrbFieldBox } from './orb-field-influence';

export const VOICE_ORB_CORE_SELECTOR = '[data-voice-orb-core]';
export const VOICE_ORB_ROOT_SELECTOR = '[data-voice-orb-root]';
export const VOICE_ORB_FALLBACK_SIZE = { width: 200, height: 200 };

export type VoiceOrbQuery = (selector: string) => Element | null;

function boxFromElement(el: Element): OrbFieldBox | null {
  if (typeof (el as HTMLElement).getBoundingClientRect !== 'function') {
    return null;
  }
  const rect = (el as HTMLElement).getBoundingClientRect();
  if (rect.width < 2 || rect.height < 2) {
    return null;
  }
  return {
    x: rect.left,
    y: rect.top,
    width: rect.width,
    height: rect.height,
  };
}

/** Live circular field for the floating orb (square-packed from the shorter axis). */
export function measureVoiceOrbLiveBox(
  query: VoiceOrbQuery = defaultQuery,
): OrbFieldBox | null {
  const core = query(VOICE_ORB_CORE_SELECTOR);
  if (core) {
    const box = boxFromElement(core);
    if (box) {
      const side = Math.min(box.width, box.height);
      const cx = box.x + box.width / 2;
      const cy = box.y + box.height / 2;
      return { x: cx - side / 2, y: cy - side / 2, width: side, height: side };
    }
  }
  const root = query(VOICE_ORB_ROOT_SELECTOR);
  if (root) {
    const box = boxFromElement(root);
    if (box) {
      const side = Math.min(box.width, box.height);
      const cx = box.x + box.width / 2;
      const cy = box.y + Math.min(box.height, side) / 2;
      return { x: cx - side / 2, y: cy - side / 2, width: side, height: side };
    }
  }
  return null;
}

export function voiceOrbBoxFromPosition(
  position: { x: number; y: number } | null | undefined,
  size: { width: number; height: number } = VOICE_ORB_FALLBACK_SIZE,
): OrbFieldBox | null {
  if (!position) {
    return null;
  }
  return { x: position.x, y: position.y, width: size.width, height: size.height };
}

function defaultQuery(selector: string): Element | null {
  if (typeof document === 'undefined') {
    return null;
  }
  return document.querySelector(selector);
}
