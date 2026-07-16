export const SANDBOX_SESSION_CONSENT_LINES = [
  'Sandbox opens a disposable copy of the project for self-improvement work.',
  'Edits stay in that copy — not your live project root, vault, or production targets.',
  'It lasts for this control-plane session only. Turn Sandbox off when you are done.',
] as const;

export function sandboxSessionHint(enabled: boolean, envForced: boolean): string {
  if (envForced) {
    return 'Sandbox is forced on by server config for this process';
  }
  if (enabled) {
    return 'Disposable sandbox API is on for this session — turn off when finished';
  }
  return 'Enable a disposable sandbox session for safe self-improvement work';
}

export function sandboxSessionLabel(enabled: boolean): string {
  return enabled ? 'Sandbox · On' : 'Sandbox';
}
