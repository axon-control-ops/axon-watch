import { describe, expect, it } from 'vitest';

import { projectEvidenceAutonomyStatus } from './operator-evidence-projector';

describe('projectEvidenceAutonomyStatus', () => {
  it('uses live action tier instead of hardcoded auto', () => {
    expect(
      projectEvidenceAutonomyStatus({
        pendingApprovals: 0,
        runPhase: null,
        actionTier: null,
      }).label,
    ).toBe('Manual');

    expect(
      projectEvidenceAutonomyStatus({
        pendingApprovals: 0,
        runPhase: null,
        actionTier: 'reversible_auto',
      }).label,
    ).toBe('Bounded auto');

    expect(
      projectEvidenceAutonomyStatus({
        pendingApprovals: 0,
        runPhase: null,
        actionTier: 'approval_gated',
      }).label,
    ).toBe('Approval gated');
  });

  it('keeps pending approvals as critical gate', () => {
    expect(
      projectEvidenceAutonomyStatus({
        pendingApprovals: 2,
        runPhase: null,
        actionTier: 'reversible_auto',
      }).label,
    ).toBe('Approval gated');
  });
});
