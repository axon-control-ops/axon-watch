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
      environment: '',
      firstRelease: '',
      lastRelease: '',
    });
  });

  it('keeps production release metadata when present', () => {
    const issues = sentryIssuesFromSignalMeta({
      signal_family: 'child_project_monitor',
      sentry_issues: [
        {
          id: '7',
          title: 'Prod boom',
          environment: 'production',
          last_release: '1.4.0',
          first_release: '1.3.9',
        },
      ],
    });
    expect(issues[0]).toMatchObject({
      id: '7',
      environment: 'production',
      lastRelease: '1.4.0',
      firstRelease: '1.3.9',
    });
  });
});
