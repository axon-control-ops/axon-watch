import type { WorkspaceRecord } from '../contracts/canonical';

import { workspacePickerPrimaryLabel } from './workspace-picker-view';

export interface IdeThreadListItem {
  thread_id: string;
  workspace_id: string;
  run_id: string | null;
  thread_kind: string;
  created_at: string;
  updated_at: string;
  preview_label: string;
}

export function ideThreadMenuLabel(thread: IdeThreadListItem): string {
  return thread.preview_label?.trim() || 'New chat';
}

export function ideThreadMenuMeta(thread: IdeThreadListItem): string {
  const updated = thread.updated_at?.trim();
  if (!updated) {
    return thread.thread_id;
  }
  return updated.replace('T', ' ').replace('Z', ' UTC');
}

export function sortIdeThreadsNewestFirst(threads: IdeThreadListItem[]): IdeThreadListItem[] {
  return [...threads].sort((left, right) => {
    const leftStamp = left.updated_at || left.created_at;
    const rightStamp = right.updated_at || right.created_at;
    return rightStamp.localeCompare(leftStamp);
  });
}

export function workspaceThreadPickerTitle(workspace: WorkspaceRecord | null): string {
  if (!workspace) {
    return 'No workspace';
  }
  return workspacePickerPrimaryLabel(workspace);
}
