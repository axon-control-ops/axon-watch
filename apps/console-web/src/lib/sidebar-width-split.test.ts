import { describe, expect, it } from 'vitest';

import {
  clampSidebarWidth,
  DEFAULT_SIDEBAR_WIDTH,
  MAX_SIDEBAR_WIDTH,
  MIN_SIDEBAR_WIDTH,
} from './sidebar-width-split';

describe('sidebar width split', () => {
  it('clamps sidebar width within bounds', () => {
    expect(clampSidebarWidth(120, 1400)).toBe(MIN_SIDEBAR_WIDTH);
    expect(clampSidebarWidth(900, 1400)).toBe(MAX_SIDEBAR_WIDTH);
    expect(clampSidebarWidth(Number.NaN, 0)).toBe(DEFAULT_SIDEBAR_WIDTH);
  });
});
