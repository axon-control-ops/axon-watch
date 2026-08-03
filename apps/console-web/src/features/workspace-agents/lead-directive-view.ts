import type { WorkspaceTaskRecord } from '../../api/tasks-api';

export type LeadDirectiveView = {
  taskId: string;
  phase: 'planning' | 'executing';
  label: string;
  instruction: string;
};

function cleanInstruction(goal: string): string {
  const compact = String(goal || '')
    .replace(/^lead\s*:\s*/i, '')
    .replace(/\s*\[from run [^\]]+\]\s*$/i, '')
    .replace(/\s*\[plan [^\]]+\]\s*/gi, ' ')
    .replace(/\s+/g, ' ')
    .trim();
  if (compact.length <= 240) {
    return compact;
  }
  return `${compact.slice(0, 239).trimEnd()}…`;
}

/** The current Lead-owned follow-up is the source of truth for the next directive. */
export function resolveLeadDirective(
  tasks: readonly WorkspaceTaskRecord[],
): LeadDirectiveView | null {
  const current = tasks
    .filter(
      (task) =>
        String(task.owner_role || '').trim().toLowerCase() === 'lead' &&
        (task.status === 'open' || task.status === 'leased'),
    )
    .sort((left, right) => right.updated_at.localeCompare(left.updated_at))[0];
  if (!current) {
    return null;
  }
  const phase = current.status === 'leased' ? 'executing' : 'planning';
  return {
    taskId: current.task_id,
    phase,
    label: phase === 'executing' ? 'Executing next step' : 'Planning next step',
    instruction: cleanInstruction(current.goal) || 'Review the latest evidence and choose the next handoff.',
  };
}
