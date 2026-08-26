import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import {
  AGENT_DOCK_COLLAPSED_KEY,
  IDE_COLLAPSED_SIDEBAR_WIDTH_PX,
  IDE_EXPLORER_COLLAPSED_KEY,
  IDE_WORKBENCH_COLLAPSED_KEY,
  LAYOUT_MODE_KEY,
  persistAgentDockCollapsed,
  persistIdeExplorerCollapsed,
  persistIdeWorkbenchCollapsed,
  persistLayoutMode,
  readStoredAgentDockCollapsed,
  readStoredIdeExplorerCollapsed,
  readStoredIdeWorkbenchCollapsed,
  readStoredLayoutMode,
  resolveIdeSidebarWidthPx,
} from './ide-layout-prefs';

class MemoryStorage {
  private store = new Map<string, string>();

  getItem(key: string): string | null {
    return this.store.get(key) ?? null;
  }

  setItem(key: string, value: string): void {
    this.store.set(key, value);
  }

  clear(): void {
    this.store.clear();
  }
}

describe('ide layout prefs', () => {
  beforeEach(() => {
    vi.stubGlobal('window', { localStorage: new MemoryStorage() });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('persists layout mode', () => {
    persistLayoutMode('ide');
    expect(readStoredLayoutMode()).toBe('ide');
    expect(window.localStorage.getItem(LAYOUT_MODE_KEY)).toBe('ide');
  });

  it('persists explorer collapse', () => {
    persistIdeExplorerCollapsed(true);
    expect(readStoredIdeExplorerCollapsed()).toBe(true);
    expect(window.localStorage.getItem(IDE_EXPLORER_COLLAPSED_KEY)).toBe('1');
  });

  it('defaults agent dock to collapsed when unset', () => {
    expect(readStoredAgentDockCollapsed()).toBe(true);
  });

  it('persists agent dock collapse', () => {
    persistAgentDockCollapsed(true);
    expect(readStoredAgentDockCollapsed()).toBe(true);
    expect(window.localStorage.getItem(AGENT_DOCK_COLLAPSED_KEY)).toBe('1');
    persistAgentDockCollapsed(false);
    expect(readStoredAgentDockCollapsed()).toBe(false);
    expect(window.localStorage.getItem(AGENT_DOCK_COLLAPSED_KEY)).toBe('0');
  });

  it('persists IDE workbench collapse', () => {
    expect(readStoredIdeWorkbenchCollapsed()).toBe(false);
    persistIdeWorkbenchCollapsed(true);
    expect(readStoredIdeWorkbenchCollapsed()).toBe(true);
    expect(window.localStorage.getItem(IDE_WORKBENCH_COLLAPSED_KEY)).toBe('1');
    persistIdeWorkbenchCollapsed(false);
    expect(readStoredIdeWorkbenchCollapsed()).toBe(false);
    expect(window.localStorage.getItem(IDE_WORKBENCH_COLLAPSED_KEY)).toBe('0');
  });

  it('resolves collapsed IDE sidebar width to the activity bar width', () => {
    expect(
      resolveIdeSidebarWidthPx({
        layoutMode: 'ide',
        explorerCollapsed: true,
        expandedSidebarWidth: 280,
        viewportWidth: 1280,
      }),
    ).toBe(IDE_COLLAPSED_SIDEBAR_WIDTH_PX);
  });

  it('resolves expanded IDE sidebar width via clamp', () => {
    const width = resolveIdeSidebarWidthPx({
      layoutMode: 'ide',
      explorerCollapsed: false,
      expandedSidebarWidth: 280,
      viewportWidth: 1280,
    });
    expect(width).toBeGreaterThan(IDE_COLLAPSED_SIDEBAR_WIDTH_PX);
  });
});
