import { describe, expect, it } from 'vitest';

import {
  buildWorkerDeliveryPipelineView,
  parseDeliveryStageFromReceiptSummary,
  workerDeliveryStageLabel,
} from './worker-delivery-pipeline-view';

describe('worker delivery pipeline view', () => {
  it('builds step states for ci_pending', () => {
    const view = buildWorkerDeliveryPipelineView({
      stage: 'ci_pending',
      draftPrUrl: 'https://github.com/org/repo/pull/1',
      attempt: 1,
    });
    expect(view?.label).toBe('CI pending');
    expect(view?.draftPrUrl).toContain('/pull/1');
    const pushed = view?.steps.find((step) => step.id === 'pushed');
    const pending = view?.steps.find((step) => step.id === 'ci_pending');
    expect(pushed?.state).toBe('done');
    expect(pending?.state).toBe('current');
  });

  it('marks error stages on the CI step', () => {
    const view = buildWorkerDeliveryPipelineView({
      stage: 'escalated',
      blocker: 'budget exhausted',
    });
    expect(view?.label).toBe('Escalated');
    expect(view?.detail).toContain('budget exhausted');
  });

  it('parses stage from receipt summary', () => {
    expect(
      parseDeliveryStageFromReceiptSummary('stage=pushed · Pushed worker/abc'),
    ).toBe('pushed');
    expect(workerDeliveryStageLabel('pr_open')).toBe('Draft PR');
  });
});
