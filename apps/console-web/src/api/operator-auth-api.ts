import { fetchJson } from './client';

export type OperatorSessionIdentity = 'local' | 'loopback' | 'operator' | 'session' | null;

export type OperatorSessionStatus = {
  authenticated: boolean;
  auth_required: boolean;
  identity: OperatorSessionIdentity;
  auth_mode?: string;
  loopback_bypass?: boolean;
  cookie_max_age_seconds?: number;
  password_enabled?: boolean;
  token_enabled?: boolean;
};

export function fetchOperatorSession(): Promise<OperatorSessionStatus> {
  return fetchJson<OperatorSessionStatus>(
    '/api/auth/session',
    { credentials: 'include' },
    'Operator session check failed',
  );
}

export async function loginOperatorSession(input: {
  username?: string;
  password: string;
}): Promise<OperatorSessionStatus> {
  await fetchJson<OperatorSessionStatus>(
    '/api/auth/session',
    {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        operator_username: input.username,
        operator_password: input.password,
      }),
    },
    'Operator sign-in failed',
  );
  const confirmed = await fetchOperatorSession();
  if (!confirmed.authenticated) {
    throw new Error(
      'Sign-in was accepted but this browser did not keep the session cookie. Stay on the same URL (localhost vs 127.0.0.1 and the port both matter) and allow cookies for this origin.',
    );
  }
  return confirmed;
}

export function logoutOperatorSession(): Promise<OperatorSessionStatus> {
  return fetchJson<OperatorSessionStatus>(
    '/api/auth/session',
    {
      method: 'DELETE',
      credentials: 'include',
    },
    'Operator sign-out failed',
  );
}
