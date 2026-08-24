import { describe, expect, it } from 'vitest';

import {
  attentionLabel,
  groupRecoveryItems,
  runPhaseForAttention,
  toRecoveryItemView,
} from './recovery-center-view';

describe('recovery center view', () => {
  it('does not invent an attention label when nothing needs recovery', () => {
    expect(attentionLabel(0)).toBe('');
    expect(runPhaseForAttention({ primaryPhase: null, attentionCount: 0 })).toBe('idle');
  });

  it('keeps a live run phase and only substitutes RECOVERY when idle plus attention', () => {
    expect(runPhaseForAttention({ primaryPhase: 'executing', attentionCount: 2 })).toBe(
      'executing',
    );
    expect(runPhaseForAttention({ primaryPhase: null, attentionCount: 2 })).toBe(
      'recovery_required',
    );
    expect(attentionLabel(2)).toBe('ATTENTION 2');
  });

  it('projects actionable copy instead of a generic failure', () => {
    const view = toRecoveryItemView({
      run_id: 'run_1',
      bucket: 'RESUMABLE',
      what_happened: 'Worker disappeared after checkpoint.',
      why_stale: 'process_pid_missing',
      recovery_action: {
        summary: 'The last checkpoint is valid. Resume is safe.',
      },
      actions: ['Resume', 'Inspect'],
    });
    expect(view.nextStep).toContain('Resume is safe');
    expect(view.actions).toContain('Resume');
  });

  it('groups unknown buckets into HUMAN_REVIEW', () => {
    const grouped = groupRecoveryItems([
      { bucket: 'STALE' },
      { bucket: 'mystery' },
    ]);
    expect(grouped.STALE).toHaveLength(1);
    expect(grouped.HUMAN_REVIEW).toHaveLength(1);
  });
});
