import { isBootstrapSummarySignal } from './operator-signal-hints';

export type SignalHandoffInput = {
  signal_id: string;
  workspace_id?: string | null;
  title: string;
  summary?: string | null;
  /** When set, used as the IDE agent prompt instead of rebuilding from title/summary. */
  task?: string | null;
  meta?: Record<string, unknown> | null;
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

function buildEmailHandoffTask(signal: SignalHandoffInput): string | null {
  const family = String(signal.meta?.signal_family ?? '').trim();
  if (family !== 'email_triage') {
    return null;
  }

  const sender = String(signal.meta?.sender ?? 'unknown sender').trim() || 'unknown sender';
  const subject =
    String(signal.meta?.subject ?? '').trim() ||
    signal.title.replace(/^Email needs follow-up:\s*/i, '').trim() ||
    signal.title;
  const detail =
    String(signal.meta?.recommended_detail ?? '').trim() || signal.summary?.trim() || '';
  const action = String(signal.meta?.recommended_action ?? '').trim();

  const parts = [`Triage email from ${sender}: "${subject}".`];
  if (detail) {
    parts.push(detail);
  }
  if (action) {
    parts.push(`Recommended action: ${action}.`);
  }
  return parts.join(' ');
}

export function buildSignalHandoffTask(signal: SignalHandoffInput): string {
  const providedTask = signal.task?.trim();
  if (providedTask) {
    return providedTask;
  }

  const emailTask = buildEmailHandoffTask(signal);
  if (emailTask) {
    return emailTask;
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
