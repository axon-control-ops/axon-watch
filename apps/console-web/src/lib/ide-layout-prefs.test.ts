import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import {
  AGENT_DOCK_COLLAPSED_KEY,
  IDE_EXPLORER_COLLAPSED_KEY,
  LAYOUT_MODE_KEY,
  persistAgentDockCollapsed,
  persistIdeExplorerCollapsed,
  persistLayoutMode,
  readStoredAgentDockCollapsed,
  readStoredIdeExplorerCollapsed,
  readStoredLayoutMode,
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

  it('persists agent dock collapse', () => {
    persistAgentDockCollapsed(true);
    expect(readStoredAgentDockCollapsed()).toBe(true);
    expect(window.localStorage.getItem(AGENT_DOCK_COLLAPSED_KEY)).toBe('1');
  });
});
