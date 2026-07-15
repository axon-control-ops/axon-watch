import { describe, expect, it } from 'vitest';

import { projectEvidenceAutonomyStatus } from './operator-evidence-projector';

describe('projectEvidenceAutonomyStatus', () => {
  it('uses live action tier instead of hardcoded auto', () => {
    expect(
      projectEvidenceAutonomyStatus({
        pendingApprovals: 0,
        runPhase: null,
        actionTier: null,
        executionAccess: 'consultative',
        workspaceSelected: true,
      }).label,
    ).toBe('Manual');

    expect(
      projectEvidenceAutonomyStatus({
        pendingApprovals: 0,
        runPhase: null,
        actionTier: 'reversible_auto',
        executionAccess: 'consultative',
        workspaceSelected: true,
      }).label,
    ).toBe('Bounded auto');

    expect(
      projectEvidenceAutonomyStatus({
        pendingApprovals: 0,
        runPhase: null,
        actionTier: 'approval_gated',
        executionAccess: 'consultative',
        workspaceSelected: true,
      }).label,
    ).toBe('Approval gated');
  });

  it('keeps pending approvals as critical gate', () => {
    expect(
      projectEvidenceAutonomyStatus({
        pendingApprovals: 2,
        runPhase: null,
        actionTier: 'reversible_auto',
        executionAccess: 'consultative',
        workspaceSelected: true,
      }).label,
    ).toBe('Approval gated');
  });

  it('requires workspace and execution-access truth before claiming bounded auto', () => {
    expect(
      projectEvidenceAutonomyStatus({
        pendingApprovals: 0,
        runPhase: null,
        actionTier: 'reversible_auto',
        executionAccess: 'consultative',
        workspaceSelected: false,
      }).label,
    ).toBe('Manual · select workspace');

    expect(
      projectEvidenceAutonomyStatus({
        pendingApprovals: 0,
        runPhase: null,
        actionTier: 'reversible_auto',
        executionAccess: null,
        workspaceSelected: true,
      }).label,
    ).toBe('Manual · access unknown');
  });

  it('distinguishes full access and active approval boundaries', () => {
    expect(
      projectEvidenceAutonomyStatus({
        pendingApprovals: 0,
        runPhase: null,
        actionTier: 'reversible_auto',
        executionAccess: 'full',
        workspaceSelected: true,
      }).label,
    ).toBe('Full access · reversible');

    expect(
      projectEvidenceAutonomyStatus({
        pendingApprovals: 0,
        runPhase: 'awaiting_approval',
        actionTier: 'reversible_auto',
        executionAccess: 'full',
        workspaceSelected: true,
      }).label,
    ).toBe('Run · awaiting approval');
  });
});
