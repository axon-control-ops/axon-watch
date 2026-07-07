import type { RunRecord } from '../contracts/canonical';

const LIVE_STOP_PHASES = new Set(['queued', 'starting', 'planning', 'executing']);

export type IdeComposerMode = 'ask' | 'plan' | 'agent';

export interface IdeComposerQueuedMessage {
  id: string;
  content: string;
  composerMode: IdeComposerMode;
  createdAt: string;
}

export const IDE_COMPOSER_QUEUE_LIMIT = 5;

export function resolveIdeStopRun(input: {
  linkedRun: RunRecord | null | undefined;
  linkedRunId: string | null;
  runs: RunRecord[];
  primaryRun: RunRecord | null | undefined;
  workspaceId: string | null;
}): RunRecord | null {
  if (input.linkedRun?.can_stop) {
    return input.linkedRun;
  }

  const linkedRunId = input.linkedRunId?.trim();
  if (linkedRunId) {
    const linked = input.runs.find((run) => run.run_id === linkedRunId);
    if (linked?.can_stop) {
      return linked;
    }
  }

  const primary = input.primaryRun;
  if (primary?.can_stop && primary.workspace_id === input.workspaceId) {
    return primary;
  }

  const workspaceId = input.workspaceId?.trim();
  if (workspaceId) {
    const liveWorkspaceRun = input.runs.find(
      (run) =>
        run.workspace_id === workspaceId &&
        run.can_stop &&
        run.status === 'running' &&
        LIVE_STOP_PHASES.has(run.phase),
    );
    if (liveWorkspaceRun) {
      return liveWorkspaceRun;
    }
  }

  return null;
}

export function shouldQueueIdeComposerSubmit(input: {
  agentBusy: boolean;
  composerMode: IdeComposerMode;
}): boolean {
  return input.agentBusy && input.composerMode === 'agent';
}

export function appendIdeComposerQueueEntry(
  queue: readonly IdeComposerQueuedMessage[],
  entry: IdeComposerQueuedMessage,
): IdeComposerQueuedMessage[] {
  return [...queue, entry].slice(-IDE_COMPOSER_QUEUE_LIMIT);
}

export function shiftIdeComposerQueue(
  queue: readonly IdeComposerQueuedMessage[],
): {
  next: IdeComposerQueuedMessage | null;
  remaining: IdeComposerQueuedMessage[];
} {
  if (!queue.length) {
    return { next: null, remaining: [] };
  }

  const [next, ...remaining] = queue;
  return { next: next ?? null, remaining };
}

export function removeIdeComposerQueueEntry(
  queue: readonly IdeComposerQueuedMessage[],
  messageId: string,
): IdeComposerQueuedMessage[] {
  return queue.filter((entry) => entry.id !== messageId);
}

export function ideComposerQueueLabel(count: number): string {
  if (count <= 0) {
    return '';
  }
  return `${count} queued message${count === 1 ? '' : 's'}`;
}
