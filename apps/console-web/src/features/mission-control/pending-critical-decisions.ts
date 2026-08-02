import type { AutonomyReceipt } from '../../api/autonomy-api';

export function softDecisionKey(item: AutonomyReceipt): string {
  const raw = String(item.dedupe_key || '').trim().toLowerCase();
  const parts = raw.split(':');
  if (parts[0] === 'failed_shift' && parts.length >= 3) {
    return `failed_shift:${parts[1]}:${parts[2]}`;
  }
  const title = String(item.title || item.kind || '').trim().toLowerCase();
  const workspace = String(item.workspace_id || '').trim().toLowerCase();
  return title ? `${workspace}:${title}` : raw || item.receipt_id;
}

/** Collapse twin failed-shift Needs-you cards for the VAXON orb HUD. */
export function collapsePendingCriticalDecisions(
  items: AutonomyReceipt[],
  workspaceId?: string | null,
): AutonomyReceipt[] {
  const scoped = items.filter(
    (item) => !workspaceId || !item.workspace_id || item.workspace_id === workspaceId,
  );
  const seen = new Set<string>();
  const collapsed: AutonomyReceipt[] = [];
  for (const item of scoped) {
    const key = softDecisionKey(item);
    if (seen.has(key)) {
      continue;
    }
    seen.add(key);
    collapsed.push(item);
  }
  return collapsed;
}
