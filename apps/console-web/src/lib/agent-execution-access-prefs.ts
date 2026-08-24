export type AgentExecutionAccess = 'consultative' | 'full';

const STORAGE_KEY = 'axon-x-agent-execution-access';
const SESSION_CONSENT_KEY = 'axon-x-full-access-session-consent';

export function normalizeAgentExecutionAccess(value: string | null | undefined): AgentExecutionAccess {
  return String(value || '').trim().toLowerCase() === 'full' ? 'full' : 'consultative';
}

export function hasFullAccessSessionConsent(): boolean {
  if (typeof window === 'undefined') {
    return false;
  }
  try {
    return window.sessionStorage.getItem(SESSION_CONSENT_KEY) === '1';
  } catch {
    return false;
  }
}

export function markFullAccessSessionConsent(): void {
  if (typeof window === 'undefined') {
    return;
  }
  try {
    window.sessionStorage.setItem(SESSION_CONSENT_KEY, '1');
  } catch {
    // ignore storage failures
  }
}

export function clearFullAccessSessionConsent(): void {
  if (typeof window === 'undefined') {
    return;
  }
  try {
    window.sessionStorage.removeItem(SESSION_CONSENT_KEY);
  } catch {
    // ignore storage failures
  }
}

export function resolveAgentExecutionAccess(): AgentExecutionAccess {
  if (typeof window === 'undefined') {
    return 'consultative';
  }
  try {
    const stored = normalizeAgentExecutionAccess(window.localStorage.getItem(STORAGE_KEY));
    if (stored === 'full' && !hasFullAccessSessionConsent()) {
      return 'consultative';
    }
    return stored;
  } catch {
    return 'consultative';
  }
}

export function persistAgentExecutionAccess(value: AgentExecutionAccess): void {
  if (typeof window === 'undefined') {
    return;
  }
  try {
    window.localStorage.setItem(STORAGE_KEY, normalizeAgentExecutionAccess(value));
  } catch {
    // ignore storage failures
  }
}

export function agentExecutionAccessLabel(value: AgentExecutionAccess): string {
  return value === 'full' ? 'Full Access' : 'Consultative';
}

export function agentExecutionAccessHint(value: AgentExecutionAccess): string {
  return value === 'full'
    ? 'Stored PC preference; effective access becomes Full inside a Full Auto or manually enabled Sandbox'
    : 'Read-only answers; no file edits or shell tools';
}
