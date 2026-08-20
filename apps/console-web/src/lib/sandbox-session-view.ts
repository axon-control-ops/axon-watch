export const SANDBOX_SESSION_CONSENT_LINES = [
  'Sandbox opens a disposable copy of the project for self-improvement work.',
  'Edits stay in that copy — not your live project root, vault, or production targets.',
  'Your per-workspace preference is durable. Dirty changes require Publish or explicit Discard.',
] as const;

export type ComposerAccessTone = 'full' | 'sandbox' | 'sandbox-full';

export function sandboxUnpromotedChangesMessage(): string {
  return 'Sandbox has unpromoted changes — use Review / Preview before publish.';
}

export function sandboxRootDirtyMessage(input: {
  bound_branch?: string;
  root_changed_paths?: string[];
}): string {
  const rootPaths = (input.root_changed_paths ?? []).slice(0, 4).join(', ');
  return `Root worktree is dirty on ${input.bound_branch || 'current branch'} (${rootPaths}). Clean root before publishing Sandbox changes.`;
}

export function sandboxStripDetailCopy(dirty: boolean): string {
  return dirty
    ? 'Review and preview this disposable checkout before publishing.'
    : 'Sandbox is active; root preview stays separate.';
}

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

/** Compact mode-chip label: e.g. Agent · Sandbox · Full */
export function buildComposerModeAccessLabel(input: {
  modeLabel: string;
  fullAccess: boolean;
  sandboxEnabled: boolean;
}): string {
  const parts = [input.modeLabel];
  if (input.sandboxEnabled) {
    parts.push('Sandbox');
  }
  if (input.fullAccess) {
    parts.push('Full');
  }
  return parts.join(' · ');
}

export function composerAccessTone(input: {
  fullAccess: boolean;
  sandboxEnabled: boolean;
}): ComposerAccessTone | null {
  if (input.sandboxEnabled && input.fullAccess) {
    return 'sandbox-full';
  }
  if (input.sandboxEnabled) {
    return 'sandbox';
  }
  if (input.fullAccess) {
    return 'full';
  }
  return null;
}

export function composerAccessBannerCopy(input: {
  fullAccess: boolean;
  sandboxEnabled: boolean;
}): { title: string; detail: string; glyph: string; tone: ComposerAccessTone } | null {
  const tone = composerAccessTone(input);
  // Full Access alone is already explained on the mode pill hover — no banner.
  if (!tone || tone === 'full') {
    return null;
  }
  if (tone === 'sandbox-full') {
    return {
      title: 'Sandbox · Full Access',
      detail: 'Disposable copy · routine tools autonomous; high-risk effects gated',
      glyph: '▣',
      tone,
    };
  }
  return {
    title: 'Sandbox',
    detail: 'Edits stay in a disposable session copy',
    glyph: '▣',
    tone,
  };
}

export function composerAccessMenuStatus(input: {
  fullAccess: boolean;
  sandboxEnabled: boolean;
}): { executionLine: string; sandboxLine: string; workerIsolationLine: string } {
  return {
    executionLine: input.fullAccess
      ? 'Full Access active — routine tools autonomous; high-risk effects gated'
      : 'Consultative — read-only tools',
    sandboxLine: input.sandboxEnabled
      ? 'Sandbox on — disposable session copy'
      : 'Sandbox off — live project',
    workerIsolationLine:
      'Full Auto supplies lazy isolated checkouts; manual workspace Sandbox remains enabled afterward',
  };
}
