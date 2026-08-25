/**
 * Honest access pill for the agent dock.
 *
 * The dock previously derived this from the composer's Sandbox toggle alone, so
 * every thread rendered "FULL ACCESS" — including watcher threads that resolve
 * to consultative, and fleet-worker threads whose writes are narrowed to a few
 * role-owned paths. Sandbox being on says where a run is isolated, not how much
 * authority it has.
 */
export type RunExecutionPolicy = {
  known: boolean;
  execution_access: string;
  write_paths?: string[];
  read_only?: boolean;
};

export type AccessPill = {
  label: string;
  tone: 'full' | 'scoped' | 'read-only' | 'unknown';
  detail: string;
};

export function agentAccessPill(input: {
  policy?: RunExecutionPolicy | null;
  sandboxEnabled: boolean;
  toolCapableMode: boolean;
}): AccessPill {
  const { policy, sandboxEnabled, toolCapableMode } = input;
  const sandboxNote = sandboxEnabled ? ' inside the disposable Sandbox' : '';

  // A resolved policy is the only source that knows the real authority.
  if (policy?.known) {
    const access = String(policy.execution_access || '').toLowerCase();
    const paths = policy.write_paths ?? [];
    if (access === 'consultative' || policy.read_only || paths.length === 0) {
      return {
        label: 'READ-ONLY',
        tone: 'read-only',
        detail: `This run resolved to ${access || 'consultative'} — it cannot write files${sandboxNote}.`,
      };
    }
    if (paths.length > 0 && !paths.includes('.')) {
      return {
        label: `SCOPED · ${paths.length} path${paths.length === 1 ? '' : 's'}`,
        tone: 'scoped',
        detail: `Writes limited to ${paths.join(', ')}${sandboxNote}.`,
      };
    }
    return {
      label: 'FULL ACCESS',
      tone: 'full',
      detail: `Unrestricted writes${sandboxNote}; external and protected effects remain gated.`,
    };
  }

  // No resolved policy yet. Never claim full access on a guess.
  if (!toolCapableMode) {
    return { label: 'READ-ONLY', tone: 'read-only', detail: 'This mode does not edit files.' };
  }
  return {
    label: 'ACCESS PENDING',
    tone: 'unknown',
    detail: sandboxEnabled
      ? 'Sandbox is on; the run has not resolved its write scope yet.'
      : 'The run has not resolved its write scope yet.',
  };
}
