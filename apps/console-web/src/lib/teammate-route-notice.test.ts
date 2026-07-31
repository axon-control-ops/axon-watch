import { describe, expect, it } from 'vitest';

import {
  teammateRouteNoticeVisibleForThread,
  type TeammateRouteNotice,
} from './teammate-route-notice';

const notice = (destinationThreadId?: string | null): TeammateRouteNotice => ({
  reason: 'role_frontend',
  toName: 'Soren',
  toRoleLabel: 'Integrations',
  fromName: 'Dana',
  previousEmployeeId: 'dana',
  previousThreadId: 'thread-dana',
  destinationThreadId,
});

describe('teammateRouteNoticeVisibleForThread', () => {
  it('hides the banner on tabs that are not the routed destination', () => {
    expect(
      teammateRouteNoticeVisibleForThread(notice('thread-soren'), 'thread-priya'),
    ).toBe(false);
  });

  it('shows the banner on the routed destination tab', () => {
    expect(
      teammateRouteNoticeVisibleForThread(notice('thread-soren'), 'thread-soren'),
    ).toBe(true);
  });

  it('keeps legacy notices without destination visible', () => {
    expect(teammateRouteNoticeVisibleForThread(notice(null), 'thread-any')).toBe(true);
  });
});
