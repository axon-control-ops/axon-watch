import type { KairoConversationPhase } from '../kairo-conversation/kairo-conversation-state';

export type GalaxyPresencePhase =
  | 'idle'
  | 'workspace_selected'
  | 'listening'
  | 'thinking'
  | 'speaking'
  | 'autonomous'
  | 'alerting';

export type GalaxyCoreOrbMode = 'idle' | 'listening' | 'busy' | 'speaking' | 'autonomous' | 'alerting';

export type GalaxyPresenceInput = {
  selectedNodeId: string | null;
  selectedNodeKind: string | null;
  conversationPhase: KairoConversationPhase;
  speechCapturing: boolean;
  kairoSpeechActive: boolean;
  agentStreamActive: boolean;
  pendingApprovals: number;
  criticalSignals: number;
  highSignals: number;
};

export type GalaxyPresenceResolved = {
  phase: GalaxyPresencePhase;
  stageClass: string;
  coreOrbMode: GalaxyCoreOrbMode;
  busy: boolean;
};

/**
 * Highest wins: autonomous > speaking > listening > thinking > alerting > workspace_selected > idle.
 */
export function resolveGalaxyPresence(input: GalaxyPresenceInput): GalaxyPresenceResolved {
  let phase: GalaxyPresencePhase = 'idle';

  if (input.agentStreamActive) {
    phase = 'autonomous';
  } else if (input.kairoSpeechActive || input.conversationPhase === 'speaking') {
    phase = 'speaking';
  } else if (input.speechCapturing || input.conversationPhase === 'listening') {
    phase = 'listening';
  } else if (input.conversationPhase === 'thinking') {
    phase = 'thinking';
  } else if (
    input.pendingApprovals > 0 ||
    input.criticalSignals > 0 ||
    input.highSignals > 0
  ) {
    phase = 'alerting';
  } else if (input.selectedNodeId && input.selectedNodeKind === 'workspace') {
    phase = 'workspace_selected';
  }

  return {
    phase,
    stageClass: `brain-galaxy-stage--presence-${phase}`,
    coreOrbMode: phaseToCoreMode(phase),
    busy: phase === 'thinking' || phase === 'speaking' || phase === 'autonomous',
  };
}

function phaseToCoreMode(phase: GalaxyPresencePhase): GalaxyCoreOrbMode {
  switch (phase) {
    case 'listening':
      return 'listening';
    case 'speaking':
      return 'speaking';
    case 'thinking':
      return 'busy';
    case 'autonomous':
      return 'autonomous';
    case 'alerting':
      return 'alerting';
    default:
      return 'idle';
  }
}
