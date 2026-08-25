import type { CompanyEmployeeRecord } from '../contracts/canonical';
import {
  buildCompanyRosterAlertBadge,
  companyFailedEmployees,
  type CompanyRosterAlertBadgeTone,
} from '../features/workspace-agents/company-roster-failure-view';

import type { IdeSearchPanelLoadState } from './ide-activity-panel-view';
import { shouldShowIdeSearchPanelAttention } from './ide-activity-panel-view';

export type IdeActivityBarTeamAttention = {
  count: number;
  tone: CompanyRosterAlertBadgeTone | null;
  hint: string | null;
};

/** Team activity-bar attention — mirrors roster alert badge tone and copy. */
export function buildIdeActivityBarTeamAttention(
  employees: readonly CompanyEmployeeRecord[] | null | undefined,
): IdeActivityBarTeamAttention {
  const count = companyFailedEmployees(employees).length;
  if (count === 0) {
    return { count: 0, tone: null, hint: null };
  }

  const badge = buildCompanyRosterAlertBadge(employees);
  return {
    count,
    tone: badge?.tone ?? 'failure',
    hint: badge?.title ?? null,
  };
}

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
  search: ' (Ctrl/Cmd+Shift+F)',
  git: ' (Ctrl/Cmd+Shift+G)',
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
    return 'Optional connector offline';
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

/** Whether the Search activity-bar button should show load-failure attention. */
export function ideActivityBarSearchNeedsAttention(input: {
  loadState: IdeSearchPanelLoadState;
  hasWorkspace: boolean;
}): boolean {
  return shouldShowIdeSearchPanelAttention(input);
}

/** Tooltip suffix for Search when workspace files failed to load. */
export function ideActivityBarSearchAttentionHint(input: {
  loadState: IdeSearchPanelLoadState;
  hasWorkspace: boolean;
}): string | null {
  if (!shouldShowIdeSearchPanelAttention(input)) {
    return null;
  }

  return 'Workspace files failed to load — open Search to retry';
}

/** Tooltip for the IDE activity-bar Search button, including load-failure attention. */
export function ideActivityBarSearchTitle(
  expanded: boolean,
  input: {
    loadState: IdeSearchPanelLoadState;
    hasWorkspace: boolean;
  },
): string {
  const base = ideActivityBarSidebarTitle('search', expanded);
  const hint = ideActivityBarSearchAttentionHint(input);
  return hint ? `${base} · ${hint}` : base;
}

/** Accessible name for the IDE activity-bar Search button, including load-failure attention. */
export function ideActivityBarSearchAriaLabel(
  expanded: boolean,
  input: {
    loadState: IdeSearchPanelLoadState;
    hasWorkspace: boolean;
  },
): string {
  const base = ideActivityBarSidebarAriaLabel('search', expanded);
  const hint = ideActivityBarSearchAttentionHint(input);
  if (!hint) {
    return base;
  }

  return `${base}, ${hint.toLowerCase()}`;
}

/** Whether the Source Control activity-bar button should show unsaved-file attention. */
export function ideActivityBarGitNeedsAttention(dirtyFileCount: number): boolean {
  return dirtyFileCount > 0;
}

/** Tooltip suffix for Source Control when editor tabs have unsaved changes. */
export function ideActivityBarGitAttentionHint(dirtyFileCount: number): string | null {
  if (dirtyFileCount <= 0) {
    return null;
  }

  return dirtyFileCount === 1
    ? '1 unsaved file'
    : `${dirtyFileCount} unsaved files`;
}

/** Tooltip for the IDE activity-bar Source Control button, including unsaved-file attention. */
export function ideActivityBarGitTitle(
  expanded: boolean,
  dirtyFileCount: number,
): string {
  const base = ideActivityBarSidebarTitle('git', expanded);
  const hint = ideActivityBarGitAttentionHint(dirtyFileCount);
  return hint ? `${base} · ${hint}` : base;
}

/** Accessible name for the IDE activity-bar Source Control button, including unsaved-file attention. */
export function ideActivityBarGitAriaLabel(
  expanded: boolean,
  dirtyFileCount: number,
): string {
  const base = ideActivityBarSidebarAriaLabel('git', expanded);
  const hint = ideActivityBarGitAttentionHint(dirtyFileCount);
  if (!hint) {
    return base;
  }

  return `${base}, ${hint.toLowerCase()}`;
}

/** Whether the Team activity-bar button should show failed-shift attention. */
export function ideActivityBarTeamNeedsAttention(
  employees: readonly CompanyEmployeeRecord[] | null | undefined,
): boolean {
  return buildIdeActivityBarTeamAttention(employees).count > 0;
}

/** Tooltip suffix for Team when roster teammates need attention after a failed or interrupted job. */
export function ideActivityBarTeamAttentionHint(
  employees: readonly CompanyEmployeeRecord[] | null | undefined,
): string | null {
  return buildIdeActivityBarTeamAttention(employees).hint;
}

/** Tooltip for the IDE activity-bar Team button, including failed-shift attention. */
export function ideActivityBarTeamTitle(
  expanded: boolean,
  employees: readonly CompanyEmployeeRecord[] | null | undefined,
): string {
  const base = ideActivityBarSidebarTitle('team', expanded);
  const hint = ideActivityBarTeamAttentionHint(employees);
  return hint ? `${base} · ${hint}` : base;
}

/** Accessible name for the IDE activity-bar Team button, including failed-shift attention. */
export function ideActivityBarTeamAriaLabel(
  expanded: boolean,
  employees: readonly CompanyEmployeeRecord[] | null | undefined,
): string {
  const base = ideActivityBarSidebarAriaLabel('team', expanded);
  const hint = ideActivityBarTeamAttentionHint(employees);
  if (!hint) {
    return base;
  }

  return `${base}, ${hint.toLowerCase()}`;
}
