import { isBootstrapSummarySignal } from './operator-signal-hints';

export type SignalHandoffInput = {
  signal_id: string;
  workspace_id?: string | null;
  title: string;
  summary?: string | null;
  /** When set, used as the IDE agent prompt instead of rebuilding from title/summary. */
  task?: string | null;
};

export type WorkspaceHandoffTarget = {
  workspace_id: string;
  display_name?: string | null;
};

export type ResolvedSignalHandoff = {
  mode: 'handoff' | 'ide_only';
  sourceWorkspaceId: string | null;
  targetWorkspaceId: string;
  task: string;
  reason: string;
};

export function buildSignalHandoffTask(signal: SignalHandoffInput): string {
  const providedTask = signal.task?.trim();
  if (providedTask) {
    return providedTask;
  }
  const summary = signal.summary?.trim();
  if (summary) {
    return `Investigate signal "${signal.title}": ${summary}`;
  }
  return `Investigate signal "${signal.title}" (${signal.signal_id}).`;
}

export function canHandoffSignalToIde(signal: SignalHandoffInput): boolean {
  return !isBootstrapSummarySignal(signal.signal_id, signal.title);
}

export function resolveSignalHandoff(
  signal: SignalHandoffInput,
  currentWorkspaceId: string | null,
  workspaces: WorkspaceHandoffTarget[],
): ResolvedSignalHandoff | null {
  if (!canHandoffSignalToIde(signal)) {
    return null;
  }

  const targetWorkspaceId =
    signal.workspace_id?.trim() || currentWorkspaceId?.trim() || workspaces[0]?.workspace_id;
  if (!targetWorkspaceId) {
    return null;
  }

  const task = buildSignalHandoffTask(signal);
  const reason = signal.signal_id;
  let sourceWorkspaceId = currentWorkspaceId?.trim() || null;

  if (!sourceWorkspaceId || sourceWorkspaceId === targetWorkspaceId) {
    const alternate = workspaces.find(
      (workspace) => workspace.workspace_id !== targetWorkspaceId,
    );
    sourceWorkspaceId = alternate?.workspace_id ?? null;
  }

  if (!sourceWorkspaceId || sourceWorkspaceId === targetWorkspaceId) {
    return {
      mode: 'ide_only',
      sourceWorkspaceId: null,
      targetWorkspaceId,
      task,
      reason,
    };
  }

  return {
    mode: 'handoff',
    sourceWorkspaceId,
    targetWorkspaceId,
    task,
    reason,
  };
}
