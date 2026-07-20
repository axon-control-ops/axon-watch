export type IdeSidebarActivityView = 'explorer' | 'search' | 'git' | 'run' | 'team';

const SIDEBAR_VIEW_LABELS: Record<IdeSidebarActivityView, string> = {
  explorer: 'Explorer',
  search: 'Search',
  git: 'Source Control',
  run: 'Run',
  team: 'Workspace team',
};

const SIDEBAR_VIEW_SHORTCUTS: Partial<Record<IdeSidebarActivityView, string>> = {
  explorer: ' (Ctrl/Cmd+B)',
};

function sidebarLabel(view: IdeSidebarActivityView): string {
  return SIDEBAR_VIEW_LABELS[view];
}

/** Tooltip for an IDE activity-bar sidebar panel button. */
export function ideActivityBarSidebarTitle(
  view: IdeSidebarActivityView,
  expanded: boolean,
): string {
  const label = `${sidebarLabel(view)}${SIDEBAR_VIEW_SHORTCUTS[view] ?? ''}`;
  return expanded ? `${label} · Click to collapse` : label;
}

/** Accessible name for an IDE activity-bar sidebar panel button. */
export function ideActivityBarSidebarAriaLabel(
  view: IdeSidebarActivityView,
  expanded: boolean,
): string {
  const label = sidebarLabel(view).toLowerCase();
  return expanded ? `Collapse ${label} sidebar` : `Expand ${label} sidebar`;
}

/** Tooltip for the IDE activity-bar explorer button. */
export function ideActivityBarExplorerTitle(expanded: boolean): string {
  return ideActivityBarSidebarTitle('explorer', expanded);
}

/** Accessible name for the IDE activity-bar explorer button. */
export function ideActivityBarExplorerAriaLabel(expanded: boolean): string {
  return ideActivityBarSidebarAriaLabel('explorer', expanded);
}

export type IdeActivityBarRunAttentionInput = {
  watchConnected: boolean;
  requiredConnectorsUnavailable: number;
  legacyConnectorGlanceVisible: boolean;
};

/** Whether the Run activity-bar button should show connector attention. */
export function ideActivityBarRunNeedsAttention(
  input: IdeActivityBarRunAttentionInput,
): boolean {
  if (!input.watchConnected) {
    return true;
  }

  return (
    input.requiredConnectorsUnavailable > 0 || input.legacyConnectorGlanceVisible
  );
}

/** Tooltip suffix for Run when watch connectors need attention. */
export function ideActivityBarRunAttentionHint(
  input: IdeActivityBarRunAttentionInput,
): string | null {
  if (!input.watchConnected) {
    return 'Watch offline';
  }

  if (input.requiredConnectorsUnavailable > 0) {
    const count = input.requiredConnectorsUnavailable;
    return count === 1
      ? '1 required connector down'
      : `${count} required connectors down`;
  }

  if (input.legacyConnectorGlanceVisible) {
    return 'Legacy Axon Local offline';
  }

  return null;
}

/** Tooltip for the IDE activity-bar Run button, including connector attention. */
export function ideActivityBarRunTitle(
  expanded: boolean,
  attention: IdeActivityBarRunAttentionInput,
): string {
  const base = ideActivityBarSidebarTitle('run', expanded);
  const hint = ideActivityBarRunAttentionHint(attention);
  return hint ? `${base} · ${hint}` : base;
}

/** Accessible name for the IDE activity-bar Run button, including connector attention. */
export function ideActivityBarRunAriaLabel(
  expanded: boolean,
  attention: IdeActivityBarRunAttentionInput,
): string {
  const base = ideActivityBarSidebarAriaLabel('run', expanded);
  const hint = ideActivityBarRunAttentionHint(attention);
  if (!hint) {
    return base;
  }

  return `${base}, ${hint.toLowerCase()}`;
}
