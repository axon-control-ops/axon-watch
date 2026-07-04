import { describe, expect, it } from 'vitest';

import {
  MOCKUP_EDITOR_SURFACE,
  MOCKUP_MONACO_THEME_ID,
  MOCKUP_TERMINAL_SURFACE,
  mockupXtermTheme,
} from './mockup-workbench-theme';

describe('mockup workbench theme', () => {
  it('uses blue-navy editor and terminal surfaces', () => {
    expect(MOCKUP_EDITOR_SURFACE).toBe('#05111b');
    expect(MOCKUP_TERMINAL_SURFACE).toBe('#061424');
  });

  it('defines mockup monaco theme id and cyan-forward xterm palette', () => {
    expect(MOCKUP_MONACO_THEME_ID).toBe('axon-watch-mockup');
    expect(mockupXtermTheme.background).toBe(MOCKUP_TERMINAL_SURFACE);
    expect(mockupXtermTheme.cyan).toBe('#00f2ff');
    expect(mockupXtermTheme.foreground).toBe('#d4e4f0');
  });
});
