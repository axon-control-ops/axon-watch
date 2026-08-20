import { describe, expect, it } from 'vitest';

import {
  DEFAULT_SESSION_COOKIE_MAX_AGE_SECONDS,
  formatSessionCookieDays,
  operatorLoginBodyCopy,
  operatorLoginFooterCopy,
} from './operator-login-copy';

describe('operator login copy', () => {
  it('states the token is a host secret, not an account, and is not stored in the page', () => {
    const body = operatorLoginBodyCopy();
    expect(body).toMatch(/no Axon-X username/i);
    expect(body).toMatch(/AXON_WATCH_OPERATOR_TOKEN/);
    expect(body).toMatch(/does not keep the token/i);
  });

  it('does not claim localhost skips login when loopback bypass is off', () => {
    const footer = operatorLoginFooterCopy({
      loopbackBypass: false,
      cookieMaxAgeSeconds: DEFAULT_SESSION_COOKIE_MAX_AGE_SECONDS,
    });
    expect(footer).not.toMatch(/opens without this step/i);
    expect(footer).toMatch(/requires the operator token even on localhost/i);
    expect(footer).toMatch(/30 days/);
    expect(footer).toMatch(/localhost and 127\.0\.0\.1/);
    expect(footer).toMatch(/5173/);
  });

  it('mentions trusted loopback only when the API says bypass is on', () => {
    const footer = operatorLoginFooterCopy({ loopbackBypass: true });
    expect(footer).toMatch(/Trusted loopback can skip this page/);
    expect(formatSessionCookieDays(undefined)).toBe(30);
  });
});
