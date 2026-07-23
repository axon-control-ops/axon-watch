import { beforeEach, describe, expect, it } from 'vitest';
import { ref } from 'vue';

import { createIdeWorkbenchChromeSlice } from './create-ide-workbench-chrome-slice';
import {
  persistWorkbenchTerminalPanelVisible,
  readStoredWorkbenchTerminalPanelVisible,
  workbenchTerminalPanelVisibleStorageKey,
} from '../../../lib/workbench-terminal-split';

const sessionStorageMock = (() => {
  let store = new Map<string, string>();
  return {
    clear() {
      store = new Map<string, string>();
    },
    getItem(key: string) {
      return store.get(key) ?? null;
    },
    key(index: number) {
      return Array.from(store.keys())[index] ?? null;
    },
    get length() {
      return store.size;
    },
    removeItem(key: string) {
      store.delete(key);
    },
    setItem(key: string, value: string) {
      store.set(key, value);
    },
  } satisfies Storage;
})();

const localStorageMock = (() => {
  let store = new Map<string, string>();
  return {
    clear() {
      store = new Map<string, string>();
    },
    getItem(key: string) {
      return store.get(key) ?? null;
    },
    key(index: number) {
      return Array.from(store.keys())[index] ?? null;
    },
    get length() {
      return store.size;
    },
    removeItem(key: string) {
      store.delete(key);
    },
    setItem(key: string, value: string) {
      store.set(key, value);
    },
  } satisfies Storage;
})();

beforeEach(() => {
  Object.defineProperty(globalThis, 'sessionStorage', {
    configurable: true,
    value: sessionStorageMock,
  });
  Object.defineProperty(globalThis, 'localStorage', {
    configurable: true,
    value: localStorageMock,
  });
  Object.defineProperty(globalThis, 'window', {
    configurable: true,
    value: globalThis,
  });
  sessionStorageMock.clear();
  localStorageMock.clear();
});

describe('createIdeWorkbenchChromeSlice terminal reveal', () => {
  it('reveals via token without writing IDE session visibility', () => {
    const ideKey = workbenchTerminalPanelVisibleStorageKey('ide');
    const operatorKey = workbenchTerminalPanelVisibleStorageKey('operator');
    sessionStorage.removeItem(ideKey);
    sessionStorage.removeItem(operatorKey);

    const ideTerminalRevealToken = ref(0);
    const slice = createIdeWorkbenchChromeSlice({
      ideTerminalRevealToken,
      ideTerminalToggleToken: ref(0),
      teamRosterRevealToken: ref(0),
      ideActivityView: ref('explorer'),
      ideExplorerCollapsed: ref(false),
      agentDockCollapsed: ref(false),
      ideAttentionPanelOpen: ref(false),
      ideBriefingPanelOpen: ref(false),
    });

    slice.revealIdeTerminalPanel();

    expect(ideTerminalRevealToken.value).toBe(1);
    expect(readStoredWorkbenchTerminalPanelVisible('ide')).toBe(false);
    expect(readStoredWorkbenchTerminalPanelVisible('operator')).toBe(false);

    // Active layout (e.g. Operator) persists for itself after CenterWorkbench opens.
    persistWorkbenchTerminalPanelVisible('operator', true);
    expect(readStoredWorkbenchTerminalPanelVisible('operator')).toBe(true);
    expect(readStoredWorkbenchTerminalPanelVisible('ide')).toBe(false);
  });
});

describe('createIdeWorkbenchChromeSlice sidebar focus', () => {
  function createSlice(overrides: Partial<Parameters<typeof createIdeWorkbenchChromeSlice>[0]> = {}) {
    return createIdeWorkbenchChromeSlice({
      ideTerminalRevealToken: ref(0),
      ideTerminalToggleToken: ref(0),
      teamRosterRevealToken: ref(0),
      ideActivityView: ref('explorer'),
      ideExplorerCollapsed: ref(true),
      agentDockCollapsed: ref(true),
      ideAttentionPanelOpen: ref(false),
      ideBriefingPanelOpen: ref(false),
      ...overrides,
    });
  }

  it('setIdeActivityView terminal opens the sidebar stub and reveals the workbench panel', () => {
    const ideActivityView = ref<'explorer' | 'terminal'>('explorer');
    const ideExplorerCollapsed = ref(true);
    const ideTerminalRevealToken = ref(0);
    const slice = createSlice({
      ideActivityView,
      ideExplorerCollapsed,
      ideTerminalRevealToken,
    });

    slice.setIdeActivityView('terminal');

    expect(ideActivityView.value).toBe('terminal');
    expect(ideExplorerCollapsed.value).toBe(false);
    expect(ideTerminalRevealToken.value).toBe(1);
  });

  it('setIdeActivityView agent expands the dock without replacing the left sidebar', () => {
    const ideActivityView = ref<'explorer' | 'agent' | 'team'>('team');
    const ideExplorerCollapsed = ref(false);
    const agentDockCollapsed = ref(true);
    const slice = createSlice({
      ideActivityView,
      ideExplorerCollapsed,
      agentDockCollapsed,
    });

    slice.setIdeActivityView('agent');

    expect(ideActivityView.value).toBe('team');
    expect(ideExplorerCollapsed.value).toBe(false);
    expect(agentDockCollapsed.value).toBe(false);
  });

  it('focusIdeSidebarView agent expands the dock and leaves Team/Explorer alone', () => {
    const ideActivityView = ref<'explorer' | 'agent' | 'terminal' | 'team'>('team');
    const ideExplorerCollapsed = ref(false);
    const agentDockCollapsed = ref(true);
    const ideTerminalRevealToken = ref(0);
    const slice = createSlice({
      ideActivityView,
      ideExplorerCollapsed,
      agentDockCollapsed,
      ideTerminalRevealToken,
    });

    slice.focusIdeSidebarView('agent');
    expect(ideActivityView.value).toBe('team');
    expect(ideExplorerCollapsed.value).toBe(false);
    expect(agentDockCollapsed.value).toBe(false);
    expect(ideTerminalRevealToken.value).toBe(0);

    slice.focusIdeSidebarView('terminal');
    expect(ideActivityView.value).toBe('terminal');
    expect(ideTerminalRevealToken.value).toBe(0);
  });

  it('revealTeamRosterForActiveEmployee opens team view and bumps the reveal token', () => {
    const ideActivityView = ref<'explorer' | 'team'>('explorer');
    const ideExplorerCollapsed = ref(true);
    const teamRosterRevealToken = ref(0);
    const slice = createSlice({
      ideActivityView,
      ideExplorerCollapsed,
      teamRosterRevealToken,
    });

    slice.revealTeamRosterForActiveEmployee();

    expect(ideActivityView.value).toBe('team');
    expect(ideExplorerCollapsed.value).toBe(false);
    expect(teamRosterRevealToken.value).toBe(1);
  });
});
