import { describe, expect, it } from 'vitest';

import {
  AGENT_DOCK_COLLAPSED_KEY,
  LAYOUT_MODE_KEY,
  persistAgentDockCollapsed,
  persistLayoutMode,
  readStoredAgentDockCollapsed,
  readStoredLayoutMode,
} from './ide-layout-prefs';
import {
  DOCK_HERO_MODE_KEY,
  persistDockHeroMode,
  readStoredDockHeroMode,
} from './dock-hero-prefs';

describe('agent dock behavior contract', () => {
  it('uses stable storage keys for layout mode and dock collapse', () => {
    expect(LAYOUT_MODE_KEY).toBe('axon-x-layout-mode-v1');
    expect(AGENT_DOCK_COLLAPSED_KEY).toBe('axon-x-agent-dock-collapsed-v2');
  });

  it('persists and restores agent dock collapsed state', () => {
    const storage = new Map<string, string>();
    const originalWindow = globalThis.window;

    Object.defineProperty(globalThis, 'window', {
      configurable: true,
      value: {
        localStorage: {
          getItem: (key: string) => storage.get(key) ?? null,
          setItem: (key: string, value: string) => {
            storage.set(key, value);
          },
        },
      },
    });

    try {
      expect(readStoredAgentDockCollapsed()).toBe(true);
      persistAgentDockCollapsed(false);
      expect(readStoredAgentDockCollapsed()).toBe(false);
      persistAgentDockCollapsed(true);
      expect(readStoredAgentDockCollapsed()).toBe(true);
      persistLayoutMode('ide');
      expect(readStoredLayoutMode()).toBe('ide');
      persistDockHeroMode('briefing');
      expect(readStoredDockHeroMode()).toBe('briefing');
      expect(DOCK_HERO_MODE_KEY).toBe('axon-x-dock-hero-mode-v1');
    } finally {
      Object.defineProperty(globalThis, 'window', {
        configurable: true,
        value: originalWindow,
      });
    }
  });
});
