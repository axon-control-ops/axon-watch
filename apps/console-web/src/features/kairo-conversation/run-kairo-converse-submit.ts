import type { Ref } from 'vue';

import {
  converseTimeoutFallbackReply,
  KairoConverseTimeoutError,
  postKairoConverse,
  resolveKairoConverseTimeoutMs,
  type KairoConverseResponse,
} from '../../lib/kairo-converse-client';
import { parseChatUiAction } from '../../lib/chat-ui-action';
import { normalizeKairoCopy } from '../../lib/kairo-entity-labels';
import { recordOperatorArtifacts } from '../../lib/operator-artifact-view';
import {
  formatConversationDisplayReply,
  sanitizeSpokenReply,
} from '../../lib/sanitize-spoken-reply';
import { recordVoiceLoopDiagnostic } from '../../lib/kairo-voice-loop-diagnostics';
import type { KairoVoiceCaptureMode } from '../../lib/kairo-voice-gate';
import type { useShellStore } from '../../stores/shell';
import { dispatchKairoConverseOutcome } from './kairo-conversation-dispatch';
import {
  mentionsBriefingSurfaceOffer,
  scheduleBriefingSurfaceOffer,
} from './conversation-briefing-surface';
import {
  kairoConversationError,
  kairoConversationPhase,
  kairoConversationReply,
  setKairoConversationPhase,
} from './kairo-conversation-state';
import { HANDOFF_CLIENT_RE } from './kairo-conversation-turn-handlers';

type ShellStore = ReturnType<typeof useShellStore>;

export type RunKairoConverseSubmitInput = {
  shell: ShellStore;
  content: string;
  answerTier: 'fast' | 'deep';
  converseStartedAt: number;
  abortSignal: AbortSignal;
  sessionId: string;
  workspaceId: string;
  contextWorkspaceId: string;
  contextSignalId: string;
  contextNodeId: string;
  voiceCaptureMode?: KairoVoiceCaptureMode;
  deliverVoiceReply: (reply: string, voiceCaptureMode?: KairoVoiceCaptureMode) => Promise<void>;
  executeConverseAction: (action: NonNullable<KairoConverseResponse['action']>) => Promise<void>;
  tryClientHandoff: (content: string) => Promise<boolean>;
  closeTurnSurface: (options?: { keepPhase?: boolean }) => void;
  clearRuntimeAssistantCue: () => void;
  pending: Ref<boolean>;
};

export async function runKairoConverseSubmit(input: RunKairoConverseSubmitInput): Promise<void> {
  const {
    shell,
    content,
    answerTier,
    converseStartedAt,
    abortSignal,
    sessionId,
    workspaceId,
    contextWorkspaceId,
    contextSignalId,
    contextNodeId,
    voiceCaptureMode,
    deliverVoiceReply,
    executeConverseAction,
    tryClientHandoff,
    closeTurnSurface,
    clearRuntimeAssistantCue,
    pending,
  } = input;

  try {
    const response = await postKairoConverse(
      {
        content,
        session_id: sessionId,
        workspace_id: workspaceId,
        use_runtime: answerTier === 'deep',
        answer_tier: answerTier,
        context_workspace_id: contextWorkspaceId,
        context_signal_id: contextSignalId,
        context_node_id: contextNodeId,
      },
      { signal: abortSignal },
    );
    clearRuntimeAssistantCue();
    recordVoiceLoopDiagnostic({
      kind: 'converse_done',
      latencyMs: Date.now() - converseStartedAt,
      phase: 'thinking',
    });
    if (response.artifacts.length) {
      recordOperatorArtifacts(response.artifacts, parseChatUiAction);
    }
    if (!response.action && HANDOFF_CLIENT_RE.test(content)) {
      if (await tryClientHandoff(content)) {
        closeTurnSurface();
        return;
      }
    }
    kairoConversationReply.value = normalizeKairoCopy(
      formatConversationDisplayReply(response.reply) || sanitizeSpokenReply(response.reply),
    );
    closeTurnSurface({ keepPhase: true });
    await dispatchKairoConverseOutcome(shell, response, executeConverseAction);
    if (mentionsBriefingSurfaceOffer(response.reply)) {
      scheduleBriefingSurfaceOffer();
    }
    await deliverVoiceReply(response.reply, voiceCaptureMode);
    if (kairoConversationPhase.value === 'thinking') {
      setKairoConversationPhase('idle');
    }
  } catch (error) {
    clearRuntimeAssistantCue();
    const timedOut = error instanceof KairoConverseTimeoutError;
    const timeoutMs = timedOut ? error.timeoutMs : resolveKairoConverseTimeoutMs(answerTier);
    if (timedOut) {
      recordVoiceLoopDiagnostic({
        kind: 'converse_timeout',
        latencyMs: Date.now() - converseStartedAt,
        delayMs: timeoutMs,
      });
      const fallback = converseTimeoutFallbackReply(timeoutMs);
      kairoConversationError.value = fallback;
      kairoConversationReply.value = fallback;
      closeTurnSurface({ keepPhase: true });
      await deliverVoiceReply(fallback, voiceCaptureMode);
      if (kairoConversationPhase.value === 'thinking') {
        setKairoConversationPhase('idle');
      }
    } else {
      recordVoiceLoopDiagnostic({
        kind: 'converse_error',
        reason: error instanceof Error ? error.message : 'unknown',
        latencyMs: Date.now() - converseStartedAt,
      });
      kairoConversationError.value =
        error instanceof Error ? error.message : 'KAIRO conversation failed';
      setKairoConversationPhase('idle');
      closeTurnSurface();
    }
  } finally {
    clearRuntimeAssistantCue();
    if (pending.value) {
      pending.value = false;
    }
    if (kairoConversationPhase.value === 'thinking') {
      setKairoConversationPhase('idle');
    }
  }
}
