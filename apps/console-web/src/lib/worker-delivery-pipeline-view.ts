/** Map worker delivery receipts / roster fields into operator-facing pipeline UI. */

export const WORKER_DELIVERY_STAGE_ORDER = [
  'changed',
  'verified',
  'committed',
  'pushed',
  'pr_open',
  'ci_pending',
  'ci_green',
] as const;

export type WorkerDeliveryUiStage =
  | (typeof WORKER_DELIVERY_STAGE_ORDER)[number]
  | 'ci_red'
  | 'repairing'
  | 'escalated'
  | 'blocked'
  | 'no_change';

export type WorkerDeliveryStepView = {
  id: WorkerDeliveryUiStage | string;
  label: string;
  state: 'done' | 'current' | 'pending' | 'error';
};

export type WorkerDeliveryPipelineView = {
  stage: string;
  label: string;
  detail: string;
  draftPrUrl: string | null;
  ciUrl: string | null;
  attempt: number | null;
  steps: WorkerDeliveryStepView[];
};

const STAGE_LABELS: Record<string, string> = {
  changed: 'Changed',
  verified: 'Verified',
  committed: 'Committed',
  pushed: 'Pushed',
  pr_open: 'Draft PR',
  ci_pending: 'CI pending',
  ci_green: 'CI green',
  ci_red: 'CI red',
  repairing: 'Repairing',
  escalated: 'Escalated',
  blocked: 'Blocked',
  no_change: 'No change',
};

export function workerDeliveryStageLabel(stage: string | null | undefined): string {
  const key = String(stage || '').trim().toLowerCase();
  return STAGE_LABELS[key] || (key ? key.replace(/_/g, ' ') : 'Idle');
}

function stageRank(stage: string): number {
  const key = stage.trim().toLowerCase();
  if (key === 'ci_red' || key === 'repairing') {
    return WORKER_DELIVERY_STAGE_ORDER.indexOf('ci_pending');
  }
  if (key === 'escalated' || key === 'blocked') {
    return WORKER_DELIVERY_STAGE_ORDER.length;
  }
  const idx = WORKER_DELIVERY_STAGE_ORDER.indexOf(
    key as (typeof WORKER_DELIVERY_STAGE_ORDER)[number],
  );
  return idx >= 0 ? idx : -1;
}

export function buildWorkerDeliveryPipelineView(input: {
  stage?: string | null;
  detail?: string | null;
  draftPrUrl?: string | null;
  ciUrl?: string | null;
  ciStatus?: string | null;
  attempt?: number | null;
  blocker?: string | null;
}): WorkerDeliveryPipelineView | null {
  const stage = String(input.stage || '').trim().toLowerCase();
  if (!stage) {
    return null;
  }
  const currentRank = stageRank(stage);
  const error = stage === 'ci_red' || stage === 'escalated' || stage === 'blocked';
  const steps: WorkerDeliveryStepView[] = WORKER_DELIVERY_STAGE_ORDER.map((id, index) => {
    let state: WorkerDeliveryStepView['state'] = 'pending';
    if (stage === 'ci_green' || index < currentRank) {
      state = 'done';
    } else if (index === currentRank) {
      state = error ? 'error' : 'current';
    }
    return { id, label: STAGE_LABELS[id] || id, state };
  });

  const detailParts = [
    input.detail?.trim(),
    input.blocker?.trim(),
    input.attempt != null ? `attempt ${input.attempt}` : '',
    input.ciStatus?.trim(),
  ].filter(Boolean);

  return {
    stage,
    label: workerDeliveryStageLabel(stage),
    detail: detailParts.join(' · '),
    draftPrUrl: input.draftPrUrl?.trim() || null,
    ciUrl: input.ciUrl?.trim() || null,
    attempt: input.attempt ?? null,
    steps,
  };
}

/** Parse stage=… from a worker_delivery receipt summary. */
export function parseDeliveryStageFromReceiptSummary(summary: string): string | null {
  const match = /(?:^|\s|·)stage=([a-z_]+)/i.exec(summary || '');
  return match?.[1]?.toLowerCase() || null;
}

export function resolveDockDeliveryPipelineView(input: {
  receiptLabels: readonly string[];
  employeePipeline?: {
    stage?: string | null;
    detail?: string | null;
    draftPrUrl?: string | null;
    ciStatus?: string | null;
  } | null;
}): WorkerDeliveryPipelineView | null {
  const latest = input.receiptLabels.find(
    (label) => /stage=/.test(label) || /worker_delivery/i.test(label),
  );
  if (!latest) {
    const employee = input.employeePipeline;
    if (!employee?.stage) {
      return null;
    }
    return buildWorkerDeliveryPipelineView({
      stage: employee.stage,
      detail: employee.detail,
      draftPrUrl: employee.draftPrUrl,
      ciStatus: employee.ciStatus,
    });
  }
  const stage = parseDeliveryStageFromReceiptSummary(latest);
  const draftMatch = /draft_pr_url=(\S+)/i.exec(latest);
  const ciMatch = /ci_run_url=(\S+)/i.exec(latest);
  const attemptMatch = /attempt=(\d+)/i.exec(latest);
  return buildWorkerDeliveryPipelineView({
    stage,
    detail: latest,
    draftPrUrl: draftMatch?.[1] ?? null,
    ciUrl: ciMatch?.[1] ?? null,
    attempt: attemptMatch ? Number(attemptMatch[1]) : null,
  });
}
