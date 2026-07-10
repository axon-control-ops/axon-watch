import { OPERATOR_PERSONA_NAME } from './operator-persona-name';

function workspaceFocusLabel(workspaceId: string | null | undefined): string {
  const clean = String(workspaceId || '').trim();
  if (!clean) {
    return '';
  }
  const withoutPrefix = clean.startsWith('workspace_') ? clean.slice('workspace_'.length) : clean;
  return withoutPrefix.replace(/_/g, ' ').trim() || clean;
}

/** Client-side mirror of control-plane `build_persona_voice_line` when briefing omits presence. */
export function buildPersonaVoiceLineFallback(input: {
  pendingApprovals: number;
  topSignalTitle?: string | null;
  topSignalWorkspaceId?: string | null;
  topSignalSummary?: string | null;
  degradedActive?: boolean;
  loadState?: 'idle' | 'loading' | 'loaded' | 'error';
  personaEnabled?: boolean;
}): string {
  const personaEnabled = input.personaEnabled !== false;
  const prefix = personaEnabled ? `${OPERATOR_PERSONA_NAME}: ` : '';
  const loadState = input.loadState ?? 'loaded';

  if (loadState === 'loading') {
    return `${prefix}Standing by while briefing loads.`;
  }
  if (loadState === 'error') {
    return `${prefix}Briefing unavailable. Check control-plane connectivity.`;
  }

  if (input.pendingApprovals > 0) {
    const suffix = input.pendingApprovals === 1 ? '' : 's';
    return personaEnabled
      ? `${prefix}${input.pendingApprovals} approval${suffix} need your review before I can continue.`
      : `${input.pendingApprovals} approval${suffix} need your review before execution can continue.`;
  }

  const title = String(input.topSignalTitle || '').trim();
  if (title) {
    const workspace = workspaceFocusLabel(input.topSignalWorkspaceId);
    const summary = String(input.topSignalSummary || '').trim();
    const detail =
      summary && !title.toLowerCase().includes(summary.toLowerCase())
        ? `${title} — ${summary}`
        : title;
    if (workspace) {
      return `${prefix}Top signal on ${workspace}: ${detail}.`;
    }
    return `${prefix}Top signal needs review: ${detail}.`;
  }

  if (input.degradedActive) {
    return `${prefix}Runtime is degraded. Review the status strip before continuing.`;
  }

  return personaEnabled
    ? `${prefix}I'm listening. Tell me what to focus on.`
    : 'Ready. Tell me what to focus on.';
}
