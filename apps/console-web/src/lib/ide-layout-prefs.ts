import type { LayoutMode } from '../stores/shell';

export const LAYOUT_MODE_KEY = 'axon-x-layout-mode-v1';
export const IDE_EXPLORER_COLLAPSED_KEY = 'axon-x-ide-explorer-collapsed-v1';
export const AGENT_DOCK_COLLAPSED_KEY = 'axon-x-agent-dock-collapsed-v1';

export type IdeActivityView = 'explorer' | 'search' | 'git' | 'run' | 'terminal' | 'agent';

export function readStoredLayoutMode(): LayoutMode | null {
  if (typeof window === 'undefined') {
    return null;
  }

  const raw = window.localStorage.getItem(LAYOUT_MODE_KEY);
  if (raw === 'operator' || raw === 'ide') {
    return raw;
  }

  return null;
}

export function persistLayoutMode(mode: LayoutMode): void {
  if (typeof window === 'undefined') {
    return;
  }

  window.localStorage.setItem(LAYOUT_MODE_KEY, mode);
}

export function readStoredIdeExplorerCollapsed(): boolean {
  if (typeof window === 'undefined') {
    return false;
  }

  return window.localStorage.getItem(IDE_EXPLORER_COLLAPSED_KEY) === '1';
}

export function persistIdeExplorerCollapsed(collapsed: boolean): void {
  if (typeof window === 'undefined') {
    return;
  }

  window.localStorage.setItem(IDE_EXPLORER_COLLAPSED_KEY, collapsed ? '1' : '0');
}

export function readStoredAgentDockCollapsed(): boolean {
  if (typeof window === 'undefined') {
    return false;
  }

  return window.localStorage.getItem(AGENT_DOCK_COLLAPSED_KEY) === '1';
}

export function persistAgentDockCollapsed(collapsed: boolean): void {
  if (typeof window === 'undefined') {
    return;
  }

  window.localStorage.setItem(AGENT_DOCK_COLLAPSED_KEY, collapsed ? '1' : '0');
}
