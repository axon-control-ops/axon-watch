import type { OperatorPresence, OperatorPresenceSettings } from '../contracts/canonical';

export const MOBILE_COMPACT_BREAKPOINT = 768;

export function readViewportWidth(
  windowLike: Pick<Window, 'innerWidth'> | null | undefined = typeof window === 'undefined'
    ? null
    : window,
): number {
  return windowLike?.innerWidth ?? 0;
}

export function resolveMobileCompactPreferred(
  presence: OperatorPresence | null | undefined,
  settings?: OperatorPresenceSettings | null,
): boolean {
  if (settings && 'mobile_compact_preferred' in settings) {
    return settings.mobile_compact_preferred;
  }
  return presence?.settings.mobile_compact_preferred ?? true;
}

export function shouldRequestViewportCompactBriefing(
  viewportWidth: number,
  presence: OperatorPresence | null | undefined,
  settings?: OperatorPresenceSettings | null,
): boolean {
  if (!(presence?.mobile.foreground_only ?? true)) {
    return false;
  }
  if (!resolveMobileCompactPreferred(presence, settings)) {
    return false;
  }
  return viewportWidth > 0 && viewportWidth < MOBILE_COMPACT_BREAKPOINT;
}

export function shouldUseMobileCompactLayout(
  viewportWidth: number,
  presence: OperatorPresence | null | undefined,
  settings?: OperatorPresenceSettings | null,
): boolean {
  if (!(presence?.mobile.foreground_only ?? true)) {
    return false;
  }
  if (presence?.mobile.compact_layout) {
    return true;
  }
  return shouldRequestViewportCompactBriefing(viewportWidth, presence, settings);
}
