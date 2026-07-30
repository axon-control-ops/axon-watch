/** Background follow of continuous-worker IDE streams for busy specialists. */

import type { CompanyEmployeeRecord } from '../contracts/canonical';

export type BusyEmployeeStreamTarget = {
  employeeId: string;
  runId: string;
  name: string;
};

export type BusyStreamAttachDecision =
  | 'skip_no_thread'
  | 'skip_no_message'
  | 'skip_already'
  | 'attach';

/**
 * Specialists with a role-tagged mid-shift run — candidates for tab open + SSE follow.
 * Includes watchers (`status: watching`) once `active_run_id` is set; excludes queued
 * fan-out assignments that have not entered dispatch yet.
 */
export function listBusyEmployeeStreamTargets(
  employees: readonly CompanyEmployeeRecord[] | null | undefined,
): BusyEmployeeStreamTarget[] {
  const targets: BusyEmployeeStreamTarget[] = [];
  for (const row of employees ?? []) {
    if (!row.enabled) {
      continue;
    }
    const runId = row.active_run_id?.trim() ?? '';
    const employeeId = row.employee_id?.trim() ?? '';
    if (!runId || !employeeId) {
      continue;
    }
    const status = (row.status ?? '').trim();
    if (status === 'assigned' || status === 'idle') {
      continue;
    }
    targets.push({
      employeeId,
      runId,
      name: (row.name ?? '').trim() || employeeId,
    });
  }
  return targets;
}

/** Resolve the Lane B agent placeholder / transcript message for an active run. */
export function resolveStreamingAgentMessageId(
  messages: readonly {
    role: string;
    run_id?: string | null;
    message_id: string;
  }[],
  runId: string,
): string | null {
  const cleaned = runId.trim();
  if (!cleaned) {
    return null;
  }
  const match = [...messages]
    .reverse()
    .find((message) => message.role === 'agent' && (message.run_id ?? '').trim() === cleaned);
  return match?.message_id?.trim() || null;
}

export function decideBusyEmployeeStreamAttach(input: {
  threadId: string | null | undefined;
  resolvedMessageId: string | null | undefined;
  alreadyActive: boolean;
  alreadyMessageId: string | null | undefined;
  /** False when UI chrome says streaming but the EventSource is gone (workspace switch). */
  hasLiveSession?: boolean;
}): BusyStreamAttachDecision {
  const threadId = input.threadId?.trim() ?? '';
  if (!threadId) {
    return 'skip_no_thread';
  }
  const messageId = input.resolvedMessageId?.trim() ?? '';
  if (!messageId) {
    return 'skip_no_message';
  }
  const hasLiveSession = input.hasLiveSession !== false;
  if (
    input.alreadyActive &&
    hasLiveSession &&
    (input.alreadyMessageId?.trim() ?? '') === messageId
  ) {
    return 'skip_already';
  }
  return 'attach';
}

export function findIdeThreadIdForEmployee(
  threads: readonly { thread_id: string; employee_id?: string | null }[],
  employeeId: string,
): string | null {
  const cleaned = employeeId.trim();
  if (!cleaned) {
    return null;
  }
  const match = threads.find((thread) => (thread.employee_id ?? '').trim() === cleaned);
  return match?.thread_id?.trim() || null;
}
