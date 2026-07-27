import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import {
  applyGalaxyPanelResizeKeyAction,
  clampGalaxyPanelWidth,
  GALAXY_LEFT_COLLAPSED_WIDTH_PX,
  GALAXY_WORKSPACES_COLLAPSED_KEY,
  persistGalaxyWorkspacesCollapsed,
  readStoredGalaxyWorkspacesCollapsed,
  resolveGalaxyPanelResizeKey,
} from './galaxy-panel-widths';

class MemoryStorage {
  private store = new Map<string, string>();

  getItem(key: string): string | null {
    return this.store.get(key) ?? null;
  }

  setItem(key: string, value: string): void {
    this.store.set(key, value);
  }

  removeItem(key: string): void {
    this.store.delete(key);
  }

  clear(): void {
    this.store.clear();
  }
}

describe('galaxy-panel-widths', () => {
  beforeEach(() => {
    vi.stubGlobal('window', { localStorage: new MemoryStorage() });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('clamps panel widths within viewport budget', () => {
    expect(clampGalaxyPanelWidth('left', 900, 1280)).toBeLessThanOrEqual(420);
    expect(clampGalaxyPanelWidth('inspector', 100, 1280)).toBe(260);
    expect(clampGalaxyPanelWidth('right', 240, 1280)).toBe(240);
  });

  it('persists workspaces collapsed preference (default expanded)', () => {
    expect(readStoredGalaxyWorkspacesCollapsed()).toBe(false);
    persistGalaxyWorkspacesCollapsed(true);
    expect(readStoredGalaxyWorkspacesCollapsed()).toBe(true);
    expect(window.localStorage.getItem(GALAXY_WORKSPACES_COLLAPSED_KEY)).toBe('1');
    expect(GALAXY_LEFT_COLLAPSED_WIDTH_PX).toBe(44);
    persistGalaxyWorkspacesCollapsed(false);
    expect(readStoredGalaxyWorkspacesCollapsed()).toBe(false);
  });

  it('maps keyboard actions for left and right edges', () => {
    expect(resolveGalaxyPanelResizeKey('ArrowRight', false, 'left')).toEqual({
      type: 'nudge',
      delta: 16,
    });
    expect(resolveGalaxyPanelResizeKey('ArrowLeft', false, 'right')).toEqual({
      type: 'nudge',
      delta: 16,
    });
    expect(resolveGalaxyPanelResizeKey('Enter', false, 'left')).toEqual({
      type: 'reset',
    });
  });

  it('applies reset to defaults', () => {
    expect(
      applyGalaxyPanelResizeKeyAction('inspector', 500, { type: 'reset' }, 1440),
    ).toBe(368);
  });
});
