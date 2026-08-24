/** Actions available on a chat terminal job card. */

import { cancelAgentTerminalJob } from '../api/workspace-api';

/**
 * Interrupt a hung job without tearing down the whole agent terminal session.
 * Failures are swallowed: the next status poll reports the real state, and a
 * cancel that lost a race should not surface as an error toast.
 */
export async function cancelAgentTerminalJobFromCard(input: {
  workspaceId: string | null | undefined;
  jobId: string;
  statuses: Record<string, string>;
}): Promise<void> {
  const workspaceId = String(input.workspaceId ?? '').trim();
  if (!workspaceId || !input.jobId) {
    return;
  }
  try {
    const record = await cancelAgentTerminalJob(workspaceId, input.jobId);
    input.statuses[input.jobId] = String(record.status || 'cancelled');
  } catch {
    /* next poll reports the real state */
  }
}

/** Copy terminal output to the clipboard, no-op where clipboard is unavailable. */
export async function copyTerminalOutput(output: string): Promise<void> {
  if (typeof navigator === 'undefined' || !navigator.clipboard || !output.trim()) {
    return;
  }
  await navigator.clipboard.writeText(output);
}
