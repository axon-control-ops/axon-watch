export type RecoveryCenterItemView = {
  runId: string;
  bucket: string;
  title: string;
  whatHappened: string;
  whyStale: string;
  nextStep: string;
  actions: string[];
  retryCount: number;
  lastProgress: string;
};

export const RECOVERY_BUCKETS = [
  'ACTIVE',
  'STALE',
  'ORPHANED',
  'RESUMABLE',
  'RETRYABLE',
  'FAILED',
  'BLOCKED',
  'HUMAN_REVIEW',
] as const;

export function attentionLabel(count: number): string {
  if (count <= 0) {
    return '';
  }
  return `ATTENTION ${count}`;
}

export function runPhaseForAttention(input: {
  primaryPhase: string | null | undefined;
  attentionCount: number;
}): string {
  if (input.primaryPhase) {
    return input.primaryPhase;
  }
  return input.attentionCount > 0 ? 'recovery_required' : 'idle';
}

export function toRecoveryItemView(item: {
  run_id: string;
  bucket: string;
  what_happened: string;
  why_stale: string;
  recovery_action?: { summary?: string };
  actions?: string[];
  retry_count?: number;
  last_meaningful_progress?: string | null;
}): RecoveryCenterItemView {
  return {
    runId: item.run_id,
    bucket: item.bucket,
    title: `${item.bucket} · ${item.run_id}`,
    whatHappened: item.what_happened || 'No summary recorded.',
    whyStale: item.why_stale || 'No stale signals.',
    nextStep: item.recovery_action?.summary || 'Inspect evidence.',
    actions: item.actions ?? ['Inspect'],
    retryCount: item.retry_count ?? 0,
    lastProgress: item.last_meaningful_progress || 'None recorded.',
  };
}

export function groupRecoveryItems<T extends { bucket: string }>(items: T[]): Record<string, T[]> {
  const groups: Record<string, T[]> = {};
  for (const bucket of RECOVERY_BUCKETS) {
    groups[bucket] = [];
  }
  for (const item of items) {
    const bucket = RECOVERY_BUCKETS.includes(item.bucket as (typeof RECOVERY_BUCKETS)[number])
      ? item.bucket
      : 'HUMAN_REVIEW';
    groups[bucket] = groups[bucket] ?? [];
    groups[bucket].push(item);
  }
  return groups;
}
