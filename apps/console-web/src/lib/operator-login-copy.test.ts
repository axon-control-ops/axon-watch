import { describe, expect, it } from 'vitest';

import {
  DEFAULT_SESSION_COOKIE_MAX_AGE_SECONDS,
  formatSessionCookieDays,
  operatorLoginBodyCopy,
  operatorLoginFooterCopy,
} from './operator-login-copy';

describe('operator login copy', () => {
  it('states operator sign-in uses a username and password without storing the password', () => {
    const body = operatorLoginBodyCopy();
    expect(body).toMatch(/operator username and password/i);
    expect(body).toMatch(/does not keep the password/i);
    expect(body).toMatch(/HttpOnly cookie/i);
  });

  it('does not claim localhost skips login when loopback bypass is off', () => {
    const footer = operatorLoginFooterCopy({
      loopbackBypass: false,
      cookieMaxAgeSeconds: DEFAULT_SESSION_COOKIE_MAX_AGE_SECONDS,
    });
    expect(footer).not.toMatch(/opens without this step/i);
    expect(footer).toMatch(/requires operator sign-in even on localhost/i);
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
