import { readActiveIdeThreadIdsByWorkspace } from '../../lib/ide-thread-tabs-prefs';
import type { ThreadSurface } from '../../lib/thread-surface-view';

export type LayoutMode = 'operator' | 'ide';
type LoadState = 'idle' | 'loading' | 'loaded' | 'error';

export type RuntimeSummaryLoadState = LoadState;
export type RuntimeStatusLoadState = LoadState;
export type InboxLoadState = LoadState;
export type RunsLoadState = LoadState;
export type WorkspacesLoadState = LoadState;
export type BriefingLoadState = LoadState;
export type WorkspaceFilesLoadState = LoadState;
export type RunMutationState =
  | 'idle'
  | 'stopping'
  | 'resuming'
  | 'approving'
  | 'rejecting'
  | 'reviewing'
  | 'completing';
export function hydrateWorkspaceSurfaceThreadIds(): Record<
  string,
  Partial<Record<ThreadSurface, string>>
> {
  const output: Record<string, Partial<Record<ThreadSurface, string>>> = {};
  for (const [workspaceId, threadId] of Object.entries(readActiveIdeThreadIdsByWorkspace())) {
    output[workspaceId] = { ide: threadId };
  }
  return output;
}
