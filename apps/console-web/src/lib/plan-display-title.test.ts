import { describe, expect, it } from 'vitest';

import { displayPlanTitle } from './plan-display-title';

describe('displayPlanTitle', () => {
  it('keeps real plan titles', () => {
    expect(displayPlanTitle('Mobile remote first')).toBe('Mobile remote first');
  });

  it('replaces exploratory openers', () => {
    expect(
      displayPlanTitle(
        'I\'ll look through the repo for the mobile control plan and any numbered options',
      ),
    ).toBe('Saved plan');
  });
});
