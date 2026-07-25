import { describe, expect, it } from 'vitest';

import { buildImplementPlanPrompt, isBuildPlanImplementPrompt } from './build-plan-prompt';

describe('buildImplementPlanPrompt', () => {
  it('detects Build Plan implement prompts', () => {
    expect(
      isBuildPlanImplementPrompt('Build this plan (plan_abc): Title\n\nImplement…'),
    ).toBe(true);
    expect(isBuildPlanImplementPrompt('How should we design this?')).toBe(false);
  });

  it('seeds an implement prompt with plan id and body', () => {
    const prompt = buildImplementPlanPrompt({
      planId: 'plan_d33969250b2e',
      title: 'Mobile remote first, then employee upgrades',
      content: '# Goal\n\n1. Tunnel\n2. Mobile shell\n3. Verify\n',
    });
    expect(prompt).toContain('Build this plan (plan_d33969250b2e):');
    expect(prompt).toContain('Mobile remote first, then employee upgrades');
    expect(prompt).toContain('# Goal');
    expect(prompt).toContain('Implement the plan steps in order');
  });

  it('sanitizes weak titles', () => {
    const prompt = buildImplementPlanPrompt({
      planId: 'plan_abcdef123456',
      title: "I'll look through the repo",
      content: '# Real plan\n\n1. One\n2. Two\n3. Three\n',
    });
    expect(prompt).toContain('Saved plan');
    expect(prompt).not.toContain("I'll look through");
  });
});
