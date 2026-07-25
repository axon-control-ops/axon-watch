import { describe, expect, it } from 'vitest';

import { shouldSoftSwitchAgentToPlan } from './composer-plan-auto-switch';

describe('composer-plan-auto-switch', () => {
  it('does not switch outside agent mode', () => {
    expect(shouldSoftSwitchAgentToPlan('plan', 'how should we design this').action).toBe('stay');
    expect(shouldSoftSwitchAgentToPlan('ask', 'architecture review').action).toBe('stay');
  });

  it('offers Plan on ambiguous planning phrases (Cursor-like suggest)', () => {
    const decision = shouldSoftSwitchAgentToPlan(
      'agent',
      'How should we approach the tunnel cutover?',
    );
    expect(decision.action).toBe('offer');
    expect(decision.shouldSwitch).toBe(false);
    expect(decision.reason).toBe('planning_phrase');
  });

  it('offers Plan on bullet-heavy prompts without execution verbs', () => {
    const decision = shouldSoftSwitchAgentToPlan(
      'agent',
      ['Please cover:', '- auth', '- tunnel', '- email routing'].join('\n'),
    );
    expect(decision.action).toBe('offer');
    expect(decision.reason).toBe('bullet_heavy');
  });

  it('leaves short agent execution prompts alone', () => {
    expect(shouldSoftSwitchAgentToPlan('agent', 'Fix the typo in README.').action).toBe('stay');
  });

  it('does not soft-switch Build Plan implement prompts', () => {
    const prompt = [
      'Build this plan (plan_abc123): Sandbox environment',
      '',
      'Implement the plan steps in order.',
      '',
      '---',
      '# Goal',
      '',
      '- Step one',
      '- Step two',
      '- Step three',
      '---',
    ].join('\n');
    const decision = shouldSoftSwitchAgentToPlan('agent', prompt);
    expect(decision.action).toBe('stay');
    expect(decision.reason).toBe('build_plan_implement');
  });

  it('does not soft-switch on a bare "plan" mention in a long Agent prompt', () => {
    const decision = shouldSoftSwitchAgentToPlan(
      'agent',
      'Please expand docs/planning/00-centre-brief.md using the saved plan we already drafted for aftercare staffing and hours.',
    );
    expect(decision.action).toBe('stay');
    expect(decision.reason).toBe('execution_plan_mention');
  });

  it('force-switches only on explicit write-a-plan intent', () => {
    const decision = shouldSoftSwitchAgentToPlan(
      'agent',
      'Write a plan for the aftercare centre brief covering ages, hours, and staffing ratios.',
    );
    expect(decision.action).toBe('switch');
    expect(decision.shouldSwitch).toBe(true);
    expect(decision.reason).toBe('explicit_plan_request');
  });

  it('lets an explicit planning request win over implementation vocabulary', () => {
    const decision = shouldSoftSwitchAgentToPlan(
      'agent',
      'Write a plan to implement the aftercare enrolment flow.',
    );
    expect(decision.action).toBe('switch');
    expect(decision.reason).toBe('explicit_plan_request');
  });

  it('keeps implementing an existing plan in Agent mode', () => {
    const decision = shouldSoftSwitchAgentToPlan(
      'agent',
      'Implement the plan for the aftercare enrolment flow.',
    );
    expect(decision.action).toBe('stay');
    expect(decision.reason).toBe('execution_plan_mention');
  });

  it('keeps long executable Lead corrections in Agent (no length force-switch)', () => {
    const danaCorrection = [
      'Dana — correction on your last status.',
      '',
      'The 23 Jul fan-out did not actually run. Those four specialist runs were ledger ghosts.',
      '',
      'Do this next:',
      '1. Do not claim work is running unless the specialist thread has a live Lane B transcript.',
      '2. After Cursor auth is healthy, re-fan-out the same backlog with role-scoped goals.',
      '3. Confirm each teammate’s thread shows an assignment note, then a real shift stream.',
      '4. Leave Priya’s payment-month fix uncommitted until I ask; CSV handoff already exists.',
      '',
      'When auth is fixed and re-fan-out starts, report again with run ids + thread evidence.',
    ].join('\n');
    const decision = shouldSoftSwitchAgentToPlan('agent', danaCorrection);
    expect(decision.action).toBe('stay');
    expect(decision.reason).toBe('execution_directive');
    expect(decision.shouldSwitch).toBe(false);
  });

  it('offers Plan for long multistep without execution verbs', () => {
    const decision = shouldSoftSwitchAgentToPlan(
      'agent',
      `${'x'.repeat(400)} then we should consider the phases first, next the rollout, finally the verify gate.`,
    );
    expect(decision.action).toBe('offer');
    expect(decision.reason).toBe('long_multistep');
  });
});
