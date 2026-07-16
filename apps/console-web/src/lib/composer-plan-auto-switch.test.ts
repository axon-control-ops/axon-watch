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
});
