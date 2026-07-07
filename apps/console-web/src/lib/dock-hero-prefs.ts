import type { DockHeroMode } from './dock-hero-mode';

export const DOCK_HERO_MODE_KEY = 'axon-x-dock-hero-mode-v1';

export function readStoredDockHeroMode(): DockHeroMode | null {
  if (typeof window === 'undefined') {
    return null;
  }

  const raw = window.localStorage.getItem(DOCK_HERO_MODE_KEY);
  if (raw === 'command' || raw === 'briefing') {
    return raw;
  }

  return null;
}

export function persistDockHeroMode(mode: DockHeroMode): void {
  if (typeof window === 'undefined') {
    return;
  }

  window.localStorage.setItem(DOCK_HERO_MODE_KEY, mode);
}
