import { describe, expect, it } from 'vitest';

import {
  COMMAND_COMPOSER_MAX_LINES_COMPACT,
  COMMAND_COMPOSER_MIN_LINES,
  resolveCommandComposerMaxLines,
} from './command-composer-autosize';

describe('command composer autosize', () => {
  it('uses a higher line cap in compact hero mode than the minimum', () => {
    expect(resolveCommandComposerMaxLines(true)).toBe(COMMAND_COMPOSER_MAX_LINES_COMPACT);
    expect(resolveCommandComposerMaxLines(false)).toBeGreaterThan(COMMAND_COMPOSER_MAX_LINES_COMPACT);
  });

  it('keeps minimum lines below compact maximum', () => {
    expect(COMMAND_COMPOSER_MIN_LINES).toBeLessThan(COMMAND_COMPOSER_MAX_LINES_COMPACT);
  });
});
