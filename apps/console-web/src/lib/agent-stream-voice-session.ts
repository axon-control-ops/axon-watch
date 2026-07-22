import type { KairoNarrationLevel, OperatorPresenceSettings } from '../contracts/canonical';

import type { AgentStreamIncrementalState } from './agent-stream-incremental';
import {
  createChatStreamVoiceNarration,
  type ChatStreamVoiceNarration,
} from './chat-stream-voice-narration';
import type { IdePresenceProfile } from './ide-presence-profile';
import { consumeIdeNarrationOverrideHint } from './ide-narration-override-hint';
import type { StreamingActivityView } from './kairo-agent-narration';

export { createAgentStreamIncrementalState } from './agent-stream-incremental';

export function createAgentStreamVoiceSession(input: {
  composerMode: string | null | undefined;
  messageId: string;
  sessionId: () => string;
  workspaceId: () => string;
  narration: () => KairoNarrationLevel;
  operatorPresenceSettings: () => OperatorPresenceSettings;
  voiceDeliveryAllowed: () => boolean;
  operatorPrompt: () => string;
  fullAccess: () => boolean;
  layoutMode: () => 'operator' | 'ide';
  idePresenceProfile: () => IdePresenceProfile;
  /** Employee neural voice for this IDE thread, when present. */
  azureVoiceId?: () => string | null | undefined;
}): ChatStreamVoiceNarration {
  const voiceNarration = createChatStreamVoiceNarration({
    composerMode: input.composerMode,
    messageId: input.messageId,
    sessionId: input.sessionId,
    workspaceId: input.workspaceId,
    narration: input.narration,
    narrateToolProgress: () => input.operatorPresenceSettings().narrate_tool_progress === true,
    voiceDeliveryAllowed: input.voiceDeliveryAllowed,
    operatorPrompt: input.operatorPrompt,
    fullAccess: input.fullAccess,
    azureVoiceId: input.azureVoiceId,
  });

  if (voiceNarration.toolNarrationEnabled) {
    consumeIdeNarrationOverrideHint({
      layoutMode: input.layoutMode(),
      idePresenceProfile: input.idePresenceProfile(),
      configuredNarration: input.operatorPresenceSettings().kairo_narration ?? 'minimal',
      effectiveNarration: input.narration(),
    });
  }

  return voiceNarration;
}

export function handleAgentStreamVoiceDelta(input: {
  voiceNarration: ChatStreamVoiceNarration;
  streamIncremental: AgentStreamIncrementalState;
  content: string;
  fullAccessNarration: boolean;
  patchActivity: (view: StreamingActivityView) => void;
}): void {
  // Parse first so completed thinking lands in the speech queue.
  const milestones = input.streamIncremental.consumeFullContent(input.content);
  input.patchActivity(input.streamIncremental.toStreamingActivityView(input.fullAccessNarration));

  // Speak closed :::thinking intent before tool milestones in this same delta.
  const spokenBlock = input.streamIncremental.takeCompletedThinkingSpeech()?.trim() ?? '';
  const spokeThinking = input.voiceNarration.maybeSpeakThinkingBlock(spokenBlock);

  if (!input.voiceNarration.toolNarrationEnabled) {
    return;
  }
  for (const milestone of milestones) {
    if (milestone.key.startsWith('thinking:')) {
      continue;
    }
    // Live thinking already said what the agent is doing — skip canned tool/edit lines.
    if (
      spokeThinking &&
      (milestone.key.startsWith('tool:') || milestone.key.startsWith('edit:'))
    ) {
      continue;
    }
    input.voiceNarration.narrateAgentMilestone(milestone, {
      preserveQueue: spokeThinking,
    });
  }
}
