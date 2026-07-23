import { describe, expect, it } from 'vitest';

import { shouldSoftSwitchAgentToPlan } from './composer-plan-auto-switch';

describe('composer-plan-auto-switch', () => {
  it('does not switch outside agent mode', () => {
    expect(shouldSoftSwitchAgentToPlan('plan', 'how should we design this').shouldSwitch).toBe(
      false,
    );
    expect(shouldSoftSwitchAgentToPlan('ask', 'architecture review').shouldSwitch).toBe(false);
  });

  it('switches on planning phrases in agent mode', () => {
    const decision = shouldSoftSwitchAgentToPlan(
      'agent',
      'How should we approach the tunnel cutover?',
    );
    expect(decision.shouldSwitch).toBe(true);
    expect(decision.reason).toBe('planning_phrase');
  });

  it('switches on bullet-heavy prompts', () => {
    const decision = shouldSoftSwitchAgentToPlan(
      'agent',
      ['Please cover:', '- auth', '- tunnel', '- email routing'].join('\n'),
    );
    expect(decision.shouldSwitch).toBe(true);
    expect(decision.reason).toBe('bullet_heavy');
  });

  it('leaves short agent execution prompts alone', () => {
    expect(
      shouldSoftSwitchAgentToPlan('agent', 'Fix the typo in README.').shouldSwitch,
    ).toBe(false);
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
    expect(decision.shouldSwitch).toBe(false);
    expect(decision.reason).toBe('build_plan_implement');
  });

  it('does not soft-switch on a bare "plan" mention in a long Agent prompt', () => {
    const decision = shouldSoftSwitchAgentToPlan(
      'agent',
      'Please expand docs/planning/00-centre-brief.md using the saved plan we already drafted for aftercare staffing and hours.',
    );
    expect(decision.shouldSwitch).toBe(false);
    expect(decision.reason).toBe('execution_plan_mention');
  });

  it('still soft-switches on explicit write-a-plan intent', () => {
    const decision = shouldSoftSwitchAgentToPlan(
      'agent',
      'Write a plan for the aftercare centre brief covering ages, hours, and staffing ratios.',
    );
    expect(decision.shouldSwitch).toBe(true);
    expect(decision.reason).toBe('planning_phrase');
  });

  it('lets an explicit planning request win over implementation vocabulary', () => {
    const decision = shouldSoftSwitchAgentToPlan(
      'agent',
      'Write a plan to implement the aftercare enrolment flow.',
    );
    expect(decision.shouldSwitch).toBe(true);
    expect(decision.reason).toBe('planning_phrase');
  });

  it('keeps implementing an existing plan in Agent mode', () => {
    const decision = shouldSoftSwitchAgentToPlan(
      'agent',
      'Implement the plan for the aftercare enrolment flow.',
    );
    expect(decision.shouldSwitch).toBe(false);
    expect(decision.reason).toBe('execution_plan_mention');
  });
});
