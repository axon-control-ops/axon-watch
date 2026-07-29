/** View helpers for automatic cross-workspace ticket routing on the task board. */

export type IncomingHandoffRow = {
  handoffId: string;
  sourceWorkspaceId: string;
  targetWorkspaceId: string;
  task: string;
  status: string;
  targetTaskId: string | null;
  routedRole: string;
  direction: 'incoming' | 'outgoing';
};

export function mapWorkspaceHandoffRows(
  items: ReadonlyArray<Record<string, unknown>> | null | undefined,
  currentWorkspaceId: string | null | undefined,
  options?: {
    /** Task status by id — used to hide completed/cancelled follow-through. */
    taskStatusById?: Record<string, string | undefined> | null;
  },
): IncomingHandoffRow[] {
  const workspaceId = String(currentWorkspaceId || '').trim();
  if (!workspaceId) {
    return [];
  }
  const taskStatusById = options?.taskStatusById ?? null;
  const rows: IncomingHandoffRow[] = [];
  for (const item of items ?? []) {
    const handoffId = String(item.handoff_id ?? '').trim();
    const sourceWorkspaceId = String(item.source_workspace_id ?? '').trim();
    const targetWorkspaceId = String(item.target_workspace_id ?? '').trim();
    const task = String(item.task ?? '').trim();
    if (!handoffId || !sourceWorkspaceId || !targetWorkspaceId || !task) {
      continue;
    }
    const status = String(item.status ?? 'recorded').trim() || 'recorded';
    if (status !== 'recorded' && status !== 'routed') {
      continue;
    }
    const targetTaskId = String(item.target_task_id ?? '').trim() || null;
    if (targetTaskId && taskStatusById) {
      const taskStatus = String(taskStatusById[targetTaskId] ?? '').trim().toLowerCase();
      if (taskStatus === 'completed' || taskStatus === 'cancelled' || taskStatus === 'failed') {
        continue;
      }
    }
    let direction: IncomingHandoffRow['direction'] | null = null;
    if (targetWorkspaceId === workspaceId) {
      direction = 'incoming';
    } else if (sourceWorkspaceId === workspaceId) {
      direction = 'outgoing';
    }
    if (!direction) {
      continue;
    }
    rows.push({
      handoffId,
      sourceWorkspaceId,
      targetWorkspaceId,
      task,
      status,
      targetTaskId,
      routedRole: String(item.routed_role ?? '').trim(),
      direction,
    });
  }
  return rows;
}

export function incomingHandoffHeadline(row: IncomingHandoffRow): string {
  const role = row.routedRole ? ` · ${row.routedRole}` : '';
  if (row.direction === 'incoming') {
    return `From ${row.sourceWorkspaceId.replace(/^workspace_/, '')}${role}`;
  }
  return `To ${row.targetWorkspaceId.replace(/^workspace_/, '')}${role}`;
}
