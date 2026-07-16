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
  for (const milestone of input.streamIncremental.consumeFullContent(input.content)) {
    if (input.voiceNarration.toolNarrationEnabled) {
      input.voiceNarration.narrateAgentMilestone(milestone);
    }
  }
  input.patchActivity(input.streamIncremental.toStreamingActivityView(input.fullAccessNarration));
  const spokenBlock = input.streamIncremental.takeCompletedThinkingSpeech()?.trim() ?? '';
  input.voiceNarration.maybeSpeakThinkingBlock(spokenBlock);
}
