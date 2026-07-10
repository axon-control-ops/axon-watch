import { describe, expect, it } from 'vitest';

import { sentryIssuesFromSignalMeta } from './sentry-signal-issues-view';

describe('sentryIssuesFromSignalMeta', () => {
  it('returns empty for non-monitor signals', () => {
    expect(
      sentryIssuesFromSignalMeta({
        signal_family: 'runtime',
        sentry_issues: [{ id: '1', title: 'x' }],
      }),
    ).toEqual([]);
  });

  it('normalizes monitor sentry issues', () => {
    const issues = sentryIssuesFromSignalMeta({
      signal_family: 'child_project_monitor',
      sentry_issues: [
        {
          id: '99',
          short_id: 'RN-99',
          title: 'Boom',
          level: 'error',
          count: 3,
          permalink: 'https://sentry.io/issues/99/',
          culprit: 'main.ts',
        },
        { id: '' },
      ],
    });
    expect(issues).toHaveLength(1);
    expect(issues[0]).toMatchObject({
      id: '99',
      shortId: 'RN-99',
      title: 'Boom',
      count: 3,
    });
  });
});
