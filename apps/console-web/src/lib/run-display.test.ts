import { describe, expect, it } from 'vitest';

import {
  formatRunDisplayName,
  formatRunIdentityLabel,
  formatRunShortId,
  humanizeRunSummary,
} from './run-display';

describe('run-display', () => {
  it('humanizes legacy command summaries', () => {
    expect(humanizeRunSummary('health')).toBe('Health check');
    expect(humanizeRunSummary('git status')).toBe('Git status');
    expect(humanizeRunSummary('read README.md')).toBe('Read README.md');
  });

  it('formats short run ids without the run_ prefix noise', () => {
    expect(formatRunShortId('run_cdb93121c6e5')).toBe('cdb931');
  });

  it('builds a friendly identity label', () => {
    expect(
      formatRunIdentityLabel({
        run_id: 'run_cdb93121c6e5',
        summary: 'health',
        detail: 'Operator command: health',
      }),
    ).toBe('Health check · #cdb931');
  });

  it('preserves already-friendly summaries', () => {
    expect(
      formatRunDisplayName({
        run_id: 'run_test',
        summary: 'Health check',
        detail: '',
      }),
    ).toBe('Health check');
  });
});
