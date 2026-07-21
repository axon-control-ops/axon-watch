export type IdeSearchPanelLoadState = 'idle' | 'loading' | 'loaded' | 'error';

export type IdeActivityPanelView =
  | 'explorer'
  | 'search'
  | 'git'
  | 'run'
  | 'team'
  | 'agent'
  | 'terminal';

const ACTIVITY_PANEL_VIEW_NAMES: Record<IdeActivityPanelView, string> = {
  explorer: 'explorer',
  search: 'search',
  git: 'source control',
  run: 'run',
  team: 'workspace team',
  agent: 'agent',
  terminal: 'terminal',
};

/** Accessible name for an IDE sidebar panel collapse control. */
export function ideActivityPanelCollapseAriaLabel(view: IdeActivityPanelView): string {
  return `Collapse ${ACTIVITY_PANEL_VIEW_NAMES[view]} panel`;
}

/** Empty or loading copy for the IDE Search sidebar when the result list is blank. */
export function buildIdeSearchPanelCaption(input: {
  query: string;
  resultCount: number;
  loadState: IdeSearchPanelLoadState;
  hasWorkspace: boolean;
}): string | null {
  if (!input.hasWorkspace) {
    return 'Open a workspace to search file paths.';
  }

  if (input.loadState === 'loading' || input.loadState === 'idle') {
    return 'Loading workspace files…';
  }

  if (input.loadState === 'error') {
    return 'Could not load workspace files — use Retry below, or check the watch connection.';
  }

  const trimmed = input.query.trim();
  if (trimmed && input.resultCount === 0) {
    return `No file paths match "${trimmed}".`;
  }

  if (input.resultCount === 0) {
    return 'No files in this workspace yet.';
  }

  if (!trimmed) {
    return 'Type to filter workspace paths.';
  }

  return null;
}

/** Whether the Search sidebar should offer a retry action after a load failure. */
export function shouldShowIdeSearchPanelRetry(input: {
  loadState: IdeSearchPanelLoadState;
  hasWorkspace: boolean;
}): boolean {
  return shouldShowIdeSearchPanelAttention(input);
}

/** Whether Search sidebar and activity-bar chrome should show load-failure attention. */
export function shouldShowIdeSearchPanelAttention(input: {
  loadState: IdeSearchPanelLoadState;
  hasWorkspace: boolean;
}): boolean {
  return input.hasWorkspace && input.loadState === 'error';
}

/** Whether the Search sidebar caption should announce through a live region. */
export function ideSearchPanelCaptionUsesLiveRegion(input: {
  loadState: IdeSearchPanelLoadState;
  hasWorkspace: boolean;
}): boolean {
  return shouldShowIdeSearchPanelAttention(input);
}

/** Accessible name for the Search sidebar file-path result list. */
export function ideSearchPanelResultsAriaLabel(input: {
  resultCount: number;
  query: string;
}): string {
  const noun = input.resultCount === 1 ? 'path' : 'paths';
  const trimmed = input.query.trim();
  if (trimmed) {
    return `${input.resultCount} file ${noun} matching "${trimmed}"`;
  }
  return `${input.resultCount} workspace file ${noun}`;
}

/** Accessible name for the Search sidebar retry control. */
export function ideSearchPanelRetryAriaLabel(loading: boolean): string {
  return loading ? 'Retrying workspace file load' : 'Retry loading workspace files';
}

/** Whether the Search sidebar should list file paths (hide stale rows while loading or errored). */
export function shouldShowIdeSearchPanelResults(input: {
  resultCount: number;
  loadState: IdeSearchPanelLoadState;
  hasWorkspace: boolean;
}): boolean {
  if (!input.hasWorkspace || input.loadState !== 'loaded') {
    return false;
  }

  return input.resultCount > 0;
}

/** Count editor tabs backed by workspace files that have unsaved edits. */
export function countIdeDirtyFileTabs(
  documents: ReadonlyArray<{ source: string; dirty?: boolean }>,
): number {
  return documents.filter((document) => document.source === 'file' && document.dirty).length;
}

/** Caption for the IDE Source Control sidebar listing unsaved file tabs. */
export function buildIdeGitPanelCaption(dirtyCount: number): string {
  return dirtyCount
    ? `${dirtyCount} file(s) with unsaved changes`
    : 'No unsaved files in the current workspace.';
}

/** Whether the Source Control sidebar should list dirty file tabs. */
export function shouldShowIdeGitPanelList(dirtyCount: number): boolean {
  return dirtyCount > 0;
}

/** Accessible name for the Source Control sidebar unsaved-file list. */
export function ideGitPanelListAriaLabel(dirtyCount: number): string {
  const noun = dirtyCount === 1 ? 'file' : 'files';
  return `${dirtyCount} unsaved workspace ${noun}`;
}

/** Whether the Source Control sidebar caption should announce through a live region. */
export function ideGitPanelCaptionUsesLiveRegion(dirtyCount: number): boolean {
  return dirtyCount > 0;
}

/** Editor document id to focus when Enter is pressed in the Source Control sidebar, or null when inert. */
export function resolveIdeGitPanelEnterDocumentId(input: {
  documents: ReadonlyArray<{ id: string }>;
  listVisible: boolean;
  highlightIndex?: number;
}): string | null {
  if (!input.listVisible || input.documents.length === 0) {
    return null;
  }

  const index = clampIdeSearchPanelHighlightIndex(
    input.highlightIndex ?? 0,
    input.documents.length,
  );

  return input.documents[index]?.id ?? null;
}

/** Clamp a Search sidebar highlight index to the current result list bounds. */
export function clampIdeSearchPanelHighlightIndex(
  index: number,
  resultCount: number,
): number {
  if (resultCount <= 0) {
    return 0;
  }

  return Math.max(0, Math.min(index, resultCount - 1));
}

/** Move the Search sidebar highlight up or down, wrapping at the list edges. */
export function stepIdeSearchPanelHighlightIndex(input: {
  currentIndex: number;
  direction: 'up' | 'down';
  resultCount: number;
}): number {
  if (input.resultCount <= 0) {
    return 0;
  }

  if (input.direction === 'down') {
    return (input.currentIndex + 1) % input.resultCount;
  }

  return input.currentIndex <= 0 ? input.resultCount - 1 : input.currentIndex - 1;
}

/** File path to open when Enter is pressed in the Search sidebar, or null when inert. */
export function resolveIdeSearchPanelEnterPath(input: {
  results: ReadonlyArray<{ path: string }>;
  resultsVisible: boolean;
  highlightIndex?: number;
}): string | null {
  if (!input.resultsVisible || input.results.length === 0) {
    return null;
  }

  const index = clampIdeSearchPanelHighlightIndex(
    input.highlightIndex ?? 0,
    input.results.length,
  );

  return input.results[index]?.path ?? null;
}

export type IdeSearchPanelEscapeAction = 'clear-query' | 'collapse-panel';

/** Escape in Search clears an active query first, then collapses the sidebar. */
export function resolveIdeSearchPanelEscapeAction(query: string): IdeSearchPanelEscapeAction {
  return query.trim() ? 'clear-query' : 'collapse-panel';
}
