import type { IdeActivityView } from './ide-layout-prefs';

export type IdeActivityBarSelectAction =
  | 'toggle-explorer'
  | 'toggle-agent'
  | 'toggle-terminal'
  | 'set-view';

/** Resolve activity-bar click: re-click collapses explorer/agent/terminal; otherwise open the view. */
export function resolveIdeActivityBarSelectAction(input: {
  view: IdeActivityView;
  currentView: IdeActivityView;
  explorerCollapsed: boolean;
  agentDockCollapsed: boolean;
  terminalPanelVisible?: boolean;
  /** When set, any of these views re-click collapses the explorer sidebar. */
  sidebarViews?: ReadonlySet<string>;
}): IdeActivityBarSelectAction {
  // Agent dock is independent of the left sidebar (Team/Explorer stay put).
  if (input.view === 'agent') {
    return 'toggle-agent';
  }

  if (input.view === 'terminal' && input.terminalPanelVisible) {
    return 'toggle-terminal';
  }

  if (input.sidebarViews?.has(input.view)) {
    if (input.currentView === input.view && !input.explorerCollapsed) {
      return 'toggle-explorer';
    }
    return 'set-view';
  }

  if (
    input.view === 'explorer' &&
    input.currentView === 'explorer' &&
    !input.explorerCollapsed
  ) {
    return 'toggle-explorer';
  }

  return 'set-view';
}
