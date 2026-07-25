import { OPERATOR_PERSONA_NAME } from './operator-persona-name';
import { explainOperatorAlert } from './operator-signal-hints';

/** Client-side mirror of control-plane `build_persona_voice_line` when briefing omits presence. */
export function buildPersonaVoiceLineFallback(input: {
  pendingApprovals: number;
  topSignalTitle?: string | null;
  topSignalWorkspaceId?: string | null;
  topSignalSummary?: string | null;
  topSignalId?: string | null;
  topSignalMeta?: Record<string, unknown> | null;
  degradedActive?: boolean;
  loadState?: 'idle' | 'loading' | 'loaded' | 'error';
  personaEnabled?: boolean;
}): string {
  const personaEnabled = input.personaEnabled !== false;
  const prefix = personaEnabled ? `${OPERATOR_PERSONA_NAME}: ` : '';
  const loadState = input.loadState ?? 'loaded';

  if (loadState === 'loading') {
    return `${prefix}Hang on — I'm still getting your status ready.`;
  }
  if (loadState === 'error') {
    return `${prefix}I can't reach the status service right now. Check that Axon is running.`;
  }

  if (input.pendingApprovals > 0) {
    const spoken = explainOperatorAlert({
      pendingApprovals: input.pendingApprovals,
      reason: 'operator_approval_required',
    }).spoken;
    return `${prefix}${spoken}`;
  }

  const title = String(input.topSignalTitle || '').trim();
  if (title) {
    const meta = { ...(input.topSignalMeta ?? {}) };
    if (input.topSignalWorkspaceId && !meta.workspace_id) {
      meta.workspace_id = input.topSignalWorkspaceId;
    }
    const spoken = explainOperatorAlert({
      signalId: input.topSignalId ?? undefined,
      title,
      summary: input.topSignalSummary,
      meta,
    }).spoken;
    return `${prefix}${spoken}`;
  }

  if (input.degradedActive) {
    const spoken = explainOperatorAlert({
      title: 'Runtime degraded',
      summary: 'Runtime is degraded',
      signalId: 'signal_runtime_degraded',
    }).spoken;
    return `${prefix}${spoken}`;
  }

  return personaEnabled
    ? `${prefix}I'm listening. Tell me what to focus on.`
    : 'Ready. Tell me what to focus on.';
}
