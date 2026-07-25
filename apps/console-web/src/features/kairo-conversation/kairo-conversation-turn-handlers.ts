import type { Ref } from 'vue';

import { postKairoConverse } from '../../lib/kairo-converse-client';
import { filterActionableOpenSignals } from '../../lib/operator-signal-count';
import type { KairoVoiceCaptureMode } from '../../lib/kairo-voice-gate';
import { useShellStore } from '../../stores/shell';
import { clearBriefingSurfaceOffer, shouldOpenBriefingFromFollowup } from './conversation-briefing-surface';
import { executeKairoConverseAction } from './execute-kairo-converse-action';
import { kairoConversationReply } from './kairo-conversation-state';

type ShellStore = ReturnType<typeof useShellStore>;

export const HANDOFF_CLIENT_RE =
  /\b(hand\s*it\s*off|hand\s*off|handoff|continue in ide|investigate in ide|open in ide)\b/i;
export const DIRECT_CONTINUE_RE =
  /^(?:a\s+)?(?:yes\s+)?(?:please\s+)?(?:continue|pick\s+up|resume|carry\s+on)\b/i;
export const CONTINUE_VOICE_RE = /\b(continue|pick up|resume|carry on)\b/i;

type DeliverVoiceReply = (
  reply: string,
  voiceCaptureMode?: KairoVoiceCaptureMode,
) => Promise<void>;

type SpeakReply = (line: string, operatorPrompt?: string) => Promise<void>;

export function createKairoConversationTurnHandlers(input: {
  shell: ShellStore;
  draft: Ref<string>;
  pending: Ref<boolean>;
  thinkingLine: Ref<string>;
  deliverVoiceReply: DeliverVoiceReply;
  speakReply: SpeakReply;
}) {
  async function executeConverseAction(
    action: NonNullable<Awaited<ReturnType<typeof postKairoConverse>>['action']>,
  ): Promise<void> {
    await executeKairoConverseAction(input.shell, action);
  }

  async function tryBriefingSurfaceFollowup(
    content: string,
    options?: { voiceCaptureMode?: KairoVoiceCaptureMode },
  ): Promise<boolean> {
    if (!shouldOpenBriefingFromFollowup(content)) {
      return false;
    }
    clearBriefingSurfaceOffer();
    input.shell.focusKairoBriefing();
    input.draft.value = '';
    input.pending.value = false;
    input.thinkingLine.value = '';
    await input.deliverVoiceReply('Opening the briefing for you.', options?.voiceCaptureMode);
    return true;
  }

  function resolveHandoffSignal() {
    const actionableInboxSignal = filterActionableOpenSignals(input.shell.inboxItems)[0];
    if (actionableInboxSignal) {
      return (
        input.shell.inboxItems.find((item) => item.signal_id === actionableInboxSignal.signal_id) ??
        actionableInboxSignal
      );
    }
    const briefingSignals = input.shell.operatorBriefing?.top_signals ?? [];
    return filterActionableOpenSignals(
      briefingSignals.map((signal) => ({
        signal_id: signal.signal_id,
        title: signal.title,
        status: 'open',
        workspace_id: signal.workspace_id,
        severity: signal.severity,
        summary: signal.summary,
      })),
    )[0];
  }

  async function tryClientHandoff(content: string): Promise<boolean> {
    if (!HANDOFF_CLIENT_RE.test(content)) {
      return false;
    }
    const topSignal = resolveHandoffSignal();
    if (!topSignal) {
      return false;
    }
    await input.shell.handoffSignalToIde(
      {
        signal_id: topSignal.signal_id,
        workspace_id: topSignal.workspace_id ?? input.shell.currentWorkspace?.workspace_id ?? '',
        title: topSignal.title,
        summary: topSignal.summary ?? topSignal.title,
      },
      { autoSubmit: true },
    );
    kairoConversationReply.value = 'Handing the top signal off to the IDE.';
    input.speakReply(kairoConversationReply.value);
    return true;
  }

  async function tryResumeCurrentRun(
    content: string,
    options?: { voiceCaptureMode?: KairoVoiceCaptureMode },
  ): Promise<boolean> {
    if (!DIRECT_CONTINUE_RE.test(content) || HANDOFF_CLIENT_RE.test(content)) {
      return false;
    }
    const run = input.shell.ideAgentLinkedRun ?? input.shell.primaryActiveRun;
    if (!run) {
      return false;
    }
    const canContinueAgentRun =
      run.mode === 'agent' && run.phase === 'executing' && !input.shell.agentStreamActive;
    if (!run.can_resume && !canContinueAgentRun) {
      return false;
    }

    await input.shell.resumePrimaryRun();
    if (input.shell.runMutationError) {
      kairoConversationReply.value = input.shell.runMutationError;
      await input.deliverVoiceReply(input.shell.runMutationError, options?.voiceCaptureMode);
      return true;
    }

    kairoConversationReply.value = 'Continuing the current run.';
    await input.deliverVoiceReply(kairoConversationReply.value, options?.voiceCaptureMode);
    return true;
  }

  return {
    executeConverseAction,
    tryBriefingSurfaceFollowup,
    tryClientHandoff,
    tryResumeCurrentRun,
  };
}
