export const DEFAULT_SESSION_COOKIE_MAX_AGE_SECONDS = 60 * 60 * 24 * 30;

export function formatSessionCookieDays(seconds: number | null | undefined): number {
  const value =
    typeof seconds === 'number' && Number.isFinite(seconds) && seconds > 0
      ? seconds
      : DEFAULT_SESSION_COOKIE_MAX_AGE_SECONDS;
  return Math.max(1, Math.round(value / 86_400));
}

export function operatorLoginBodyCopy(): string {
  return (
    'Use the operator username and password configured for this host. ' +
    'This page does not keep the password. The control plane exchanges it for an HttpOnly cookie.'
  );
}

export function operatorLoginFooterCopy(input: {
  loopbackBypass?: boolean | null;
  cookieMaxAgeSeconds?: number | null;
}): string {
  const days = formatSessionCookieDays(input.cookieMaxAgeSeconds);
  const persistence =
    `After a successful sign-in, this browser keeps that session for ${days} days ` +
    'on this exact origin (scheme + host + port). localhost and 127.0.0.1 are different, ' +
    'and port 5173 is not port 4173. Sign out, clearing cookies, or rotating the ' +
    'deployment token brings this page back.';
  if (input.loopbackBypass) {
    return `Trusted loopback can skip this page. ${persistence}`;
  }
  return (
    'This host currently requires operator sign-in even on localhost ' +
    '(remote reachability or loopback bypass off). ' +
    persistence
  );
}
