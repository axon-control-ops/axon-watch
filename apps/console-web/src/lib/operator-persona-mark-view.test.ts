import { describe, expect, it } from 'vitest';

import {
  PERSONA_MARK_SIZE_PX,
} from './operator-persona-mark-view';

describe('operator persona mark view', () => {
  it('defines size tokens for each mark variant', () => {
    expect(PERSONA_MARK_SIZE_PX.xs).toBeGreaterThan(0);
    expect(PERSONA_MARK_SIZE_PX.orb).toBeGreaterThan(PERSONA_MARK_SIZE_PX.xs);
  });

  it('exports glyph size tokens', () => {
    expect(Object.keys(PERSONA_MARK_SIZE_PX).sort()).toEqual(['lg', 'md', 'orb', 'sm', 'xs']);
  });
});
