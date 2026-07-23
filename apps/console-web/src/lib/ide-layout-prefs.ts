import type { LayoutMode } from '../stores/shell';
import { clampSidebarWidth } from './sidebar-width-split';

export const LAYOUT_MODE_KEY = 'axon-x-layout-mode-v1';
export const IDE_EXPLORER_COLLAPSED_KEY = 'axon-x-ide-explorer-collapsed-v1';
export const AGENT_DOCK_COLLAPSED_KEY = 'axon-x-agent-dock-collapsed-v1';
/** Activity bar width when the IDE explorer panel is fully collapsed (matches --ide-activity-width). */
export const IDE_COLLAPSED_SIDEBAR_WIDTH_PX = 42;

export function resolveIdeSidebarWidthPx(input: {
  layoutMode: LayoutMode;
  explorerCollapsed: boolean;
  expandedSidebarWidth: number;
  viewportWidth: number;
}): number {
  if (input.layoutMode === 'ide' && input.explorerCollapsed) {
    return IDE_COLLAPSED_SIDEBAR_WIDTH_PX;
  }

  return clampSidebarWidth(input.expandedSidebarWidth, input.viewportWidth);
}

export type IdeActivityView =
  | 'explorer'
  | 'search'
  | 'git'
  | 'run'
  | 'team'
  | 'terminal'
  | 'agent';

/** Boot default for the IDE left activity panel (Team, not Explorer). */
export const DEFAULT_IDE_ACTIVITY_VIEW: IdeActivityView = 'team';

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
