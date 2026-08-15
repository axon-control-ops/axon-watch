import { describe, expect, it } from 'vitest';

import { parseLeadReviewMessage, parseFindingLine } from './lead-review-rollups';

describe('parseFindingLine', () => {
  it('parses owner, status, outcome, excerpt, and run ids', () => {
    expect(
      parseFindingLine(
        'Marco: completed (tests passed) — npm test green · runs run_abc, run_def',
      ),
    ).toEqual({
      owner: 'Marco',
      status: 'completed',
      outcome: 'tests passed',
      excerpt: 'npm test green',
      runIds: ['run_abc', 'run_def'],
    });
  });
});

describe('parseLeadReviewMessage', () => {
  it('parses a structured team rollup', () => {
    const parsed = parseLeadReviewMessage(
      [
        'VAXON: Lead team rollup is ready for your review.',
        'Goal: Fix parent homework upload',
        'Plan: plan_abc123',
        'Outcome: Backend verification passed; frontend pending.',
        '- Marco: completed (tests passed) — npm test green · runs run_abc',
        '- Priya: idle (waiting)',
        'Open Dana\'s Lead thread for the full narrative, or ask me what to do next.',
      ].join('\n'),
    );

    expect(parsed.kind).toBe('team_rollup');
    expect(parsed.goal).toBe('Fix parent homework upload');
    expect(parsed.planId).toBe('plan_abc123');
    expect(parsed.outcome).toContain('Backend verification');
    expect(parsed.findings).toHaveLength(2);
    expect(parsed.findings[0]?.owner).toBe('Marco');
    expect(parsed.footer).toContain('Open Dana');
  });

  it('parses an ad-hoc specialist handoff flash', () => {
    const parsed = parseLeadReviewMessage(
      [
        'VAXON: Marco (backend) just completed.',
        'Workspace: workspace_dashpro',
        'Run: run_b0f81ce60e2e',
        'Lead summary: Verification passed with 346 test suites.',
        'Lead next: Dispatch frontend follow-up.',
        'Ask me REPORT / update anytime — I keep fleet state from Lead handoffs.',
      ].join('\n'),
    );

    expect(parsed.kind).toBe('adhoc_handoff');
    expect(parsed.workspaceId).toBe('workspace_dashpro');
    expect(parsed.runId).toBe('run_b0f81ce60e2e');
    expect(parsed.outcome).toContain('346 test suites');
    expect(parsed.leadNext).toContain('frontend follow-up');
  });
});
