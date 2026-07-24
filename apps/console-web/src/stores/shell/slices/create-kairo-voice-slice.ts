import type { ComputedRef, Ref } from 'vue';

import type {
  OperatorBriefing,
  OperatorPresenceSettings,
  RuntimeSummary,
  SpokenAlertEligibility,
  WorkspaceRecord,
  KairoNarrationLevel,
} from '../../../contracts/canonical';
import {
  appendBriefingVoiceTranscriptEntry,
  type BriefingVoiceTranscriptEntry,
} from '../../../lib/briefing-voice-transcript';
import type { KairoPresenceState } from '../../../lib/kairo-presence';
import { deliverSpokenOperatorAlert } from '../../../lib/spoken-alert-delivery';
import {
  type KairoVoiceSpeaker,
  vaxonVoiceSpeaker,
} from '../../../lib/kairo-voice-utterance';
import { buildKairoSpeechSessionId } from '../../../lib/kairo-speech-session';
import { ideVoiceSpeechAllowed } from '../../../lib/ide-voice-strip';
import { postKairoSpeak } from '../../../lib/kairo-speak-client';
import {
  onKairoVoiceIdle,
  pauseKairoPlayback,
  resumeKairoPlayback,
  speakKairoLine,
  stopKairoPlayback,
  subscribeKairoVoiceSpeaking,
  isKairoVoiceSpeaking,
} from '../../../lib/kairo-voice-playback';
import {
  flushKairoSpeechQueue,
  interruptKairoSpeechQueue,
  isKairoSpeechQueueBusy,
} from '../../../lib/kairo-voice-queue';
import {
  onSpeechQueueIdle,
  subscribeSpeechQueueSpeaking,
} from '../../../lib/speech-queue';
import {
  setKairoConversationPhase,
  kairoConversationPhase,
} from '../../../features/kairo-conversation/kairo-conversation-state';
import { scheduleBriefingSurfaceOffer } from '../../../features/kairo-conversation/conversation-briefing-surface';
import { resolveKairoPresenceClickTarget } from '../../../lib/kairo-presence-action';
import type { LayoutMode } from '../types';
import type { IdeComposerActivity } from '../../../lib/agent-dock-activity-view';

interface CreateKairoVoiceSliceInput {
  currentWorkspace: Ref<WorkspaceRecord | null>;
  operatorPresenceSettings: Ref<OperatorPresenceSettings>;
  operatorBriefing: Ref<OperatorBriefing | null>;
  runtimeSummary: Ref<RuntimeSummary | null>;
  layoutMode: Ref<LayoutMode>;
  pendingApprovalsCount: ComputedRef<number>;
  kairoSpeechQueueActive: Ref<boolean>;
  kairoVoiceEngineActive: Ref<boolean>;
  kairoVoicePaused: Ref<boolean>;
  ideComposerActivity: Ref<IdeComposerActivity | null>;
  activeWorkspaceFilePath: ComputedRef<string | null>;
  workspaces: Ref<WorkspaceRecord[]>;
  effectiveKairoNarrationLevel: ComputedRef<KairoNarrationLevel>;
  kairoPresenceState: ComputedRef<KairoPresenceState>;
  briefingVoiceTranscript: Ref<BriefingVoiceTranscriptEntry[]>;
  getWorkspaceSurfaceThreadId: (workspaceId: string, surface: 'operator' | 'ide') => string | null;
  currentThreadSurface: () => 'operator' | 'ide';
  focusAttentionSidebar: () => void;
  focusKairoBriefing: () => void;
}

export function createKairoVoiceSlice(input: CreateKairoVoiceSliceInput) {
  function kairoSpeechSessionId(): string {
    const workspaceId = input.currentWorkspace.value?.workspace_id ?? '';
    const threadId = workspaceId
      ? input.getWorkspaceSurfaceThreadId(workspaceId, input.currentThreadSurface())
      : null;
    return buildKairoSpeechSessionId(workspaceId, threadId);
  }

  function voiceDeliveryAllowed(): boolean {
    return ideVoiceSpeechAllowed({
      layoutMode: input.layoutMode.value,
      settings: input.operatorPresenceSettings.value,
    });
  }

  function stopKairoSpeech(): void {
    flushKairoSpeechQueue('stopped');
    stopKairoPlayback();
    input.kairoVoicePaused.value = false;
    if (kairoConversationPhase.value === 'speaking') {
      setKairoConversationPhase('idle');
    }
  }

  function pauseKairoSpeech(): boolean {
    const paused = pauseKairoPlayback();
    input.kairoVoicePaused.value = paused;
    return paused;
  }

  function resumeKairoSpeech(): boolean {
    const resumed = resumeKairoPlayback();
    if (resumed) {
      input.kairoVoicePaused.value = false;
      if (kairoConversationPhase.value === 'idle') {
        setKairoConversationPhase('speaking');
      }
    }
    return resumed;
  }

  function interruptKairoVoice(): void {
    void interruptKairoSpeechQueue('barge_in');
    input.kairoVoicePaused.value = false;
    if (kairoConversationPhase.value === 'speaking') {
      setKairoConversationPhase('idle');
    }
  }

  async function speakKairoConversationLine(
    line: string,
    options?: {
      operatorPrompt?: string;
      skipSpeakApi?: boolean;
      azureVoiceId?: string | null;
      speaker?: KairoVoiceSpeaker | null;
    },
  ): Promise<void> {
    const trimmed = line.trim();
    const configuredNarration = input.operatorPresenceSettings.value.kairo_narration ?? 'minimal';
    if (
      !trimmed ||
      !voiceDeliveryAllowed() ||
      input.operatorPresenceSettings.value.privacy_mode ||
      configuredNarration === 'off'
    ) {
      if (kairoConversationPhase.value === 'thinking') {
        setKairoConversationPhase('idle');
      }
      return;
    }

    setKairoConversationPhase('speaking');
    input.kairoVoicePaused.value = false;
    let message = trimmed;
    const narration = configuredNarration;
    const operatorPrompt = options?.operatorPrompt?.trim() ?? '';
    const skipSpeakApi = options?.skipSpeakApi === true;

    if (!skipSpeakApi) {
      try {
        const response = await postKairoSpeak({
          event_type: 'conversation_reply',
          context: {
            fallback: trimmed,
            reply: trimmed,
            operator_prompt: operatorPrompt,
            pending_approvals: input.pendingApprovalsCount.value,
            top_signal_title: input.operatorBriefing.value?.top_signals[0]?.title ?? '',
            active_run_count: input.operatorBriefing.value?.active_runs.length ?? 0,
            degraded_active: input.operatorBriefing.value?.degraded.active ?? false,
            speaker_kind: options?.speaker?.kind === 'employee' || options?.azureVoiceId ? 'agent' : 'vaxon',
          },
          session_id: kairoSpeechSessionId(),
          workspace_id: input.currentWorkspace.value?.workspace_id ?? '',
          narration,
          use_runtime: narration === 'conversational',
        });
        if (response.line?.trim()) {
          message = response.line.trim();
        }
      } catch {
        // Fall back to the raw reply when the speak endpoint is unavailable.
      }
    }

    const speaker =
      options?.speaker ??
      (options?.azureVoiceId?.trim()
        ? {
            kind: 'employee' as const,
            id: `voice:${options.azureVoiceId.trim()}`,
            name: options.operatorPrompt?.replace(/^Teammate\s+/i, '').trim() || 'Teammate',
            roleLabel: 'Agent',
            azureVoiceId: options.azureVoiceId.trim(),
          }
        : vaxonVoiceSpeaker());
    const playback = await speakKairoLine(message, {
      priority: 'conversation',
      speechRate: input.operatorPresenceSettings.value.speech_rate,
      speechPitch: input.operatorPresenceSettings.value.speech_pitch,
      azureVoiceId: options?.azureVoiceId?.trim() || undefined,
      speaker,
    });
  }

  function handleKairoPresenceAction(): void {
    const target = resolveKairoPresenceClickTarget({
      paused: input.kairoVoicePaused.value,
      voiceBusy:
        input.kairoSpeechQueueActive.value ||
        input.kairoVoiceEngineActive.value ||
        isKairoSpeechQueueBusy() ||
        kairoConversationPhase.value === 'speaking' ||
        kairoConversationPhase.value === 'thinking',
      layoutMode: input.layoutMode.value,
      state: input.kairoPresenceState.value,
    });
    if (target === 'resume') {
      resumeKairoSpeech();
      return;
    }
    if (target === 'pause') {
      pauseKairoSpeech();
      return;
    }
    if (target === 'interrupt') {
      interruptKairoVoice();
      setKairoConversationPhase('idle');
      return;
    }
    if (target === 'attention') {
      input.focusAttentionSidebar();
      return;
    }
    input.focusKairoBriefing();
  }


  async function deliverKairoSpokenAlert(alert: SpokenAlertEligibility): Promise<void> {
    if (!voiceDeliveryAllowed()) {
      return;
    }
    if (!alert.eligible || !input.operatorPresenceSettings.value.spoken_alerts_enabled) {
      return;
    }
    if (input.operatorPresenceSettings.value.privacy_mode) {
      return;
    }
    if (input.effectiveKairoNarrationLevel.value === 'off') {
      return;
    }

    let eventType = 'alert';
    const topSignal = input.operatorBriefing.value?.top_signals[0];
    const context: Record<string, unknown> = {
      fallback: alert.message,
      pending_approvals: input.pendingApprovalsCount.value,
      signal_id: alert.signal_id ?? topSignal?.signal_id ?? '',
      top_signal_id: alert.signal_id ?? topSignal?.signal_id ?? '',
      top_signal_title: topSignal?.title ?? '',
      top_signal_workspace_id: topSignal?.workspace_id ?? '',
      top_signal_summary: topSignal?.summary ?? '',
      degraded_active: Boolean(input.runtimeSummary.value?.degraded.active),
    };

    if (alert.reason === 'operator_approval_required') {
      eventType = 'approval_literal';
      context.literal_line = alert.message.replace(/^(?:VAXON|NAXON|X|KAIRO):\s*/i, '').trim();
    }

    let message = '';
    try {
      const response = await postKairoSpeak({
        event_type: eventType,
        context,
        session_id: kairoSpeechSessionId(),
        workspace_id: input.currentWorkspace.value?.workspace_id ?? '',
        narration: input.effectiveKairoNarrationLevel.value,
      });
      if (response.source === 'skipped' || !response.line?.trim()) {
        return;
      }
      message = response.line.trim();
    } catch {
      return;
    }

    void deliverSpokenOperatorAlert(
      {
        eligible: true,
        reason: alert.reason,
        signal_id: alert.signal_id,
        message,
      },
      sessionStorage,
      { speaker: vaxonVoiceSpeaker() },
    );
  }

  async function speakOperatorBriefing(): Promise<void> {
    if (!voiceDeliveryAllowed() || input.operatorPresenceSettings.value.privacy_mode) {
      return;
    }
    if (input.effectiveKairoNarrationLevel.value === 'off') {
      return;
    }

    const notice = input.operatorBriefing.value?.notice?.trim() ?? '';
    const advise = input.operatorBriefing.value?.advise?.trim() ?? '';
    if (!notice && !advise) {
      return;
    }

    try {
      const response = await postKairoSpeak({
        event_type: 'briefing',
        context: {
          notice,
          advise,
          workspace_id: input.currentWorkspace.value?.workspace_id ?? '',
          pending_approvals: input.pendingApprovalsCount.value,
          top_signal_title: input.operatorBriefing.value?.top_signals[0]?.title ?? '',
        },
        session_id: kairoSpeechSessionId(),
        workspace_id: input.currentWorkspace.value?.workspace_id ?? '',
        narration: input.effectiveKairoNarrationLevel.value,
        use_runtime: true,
      });
      if (response.source === 'skipped' || !response.line?.trim()) {
        return;
      }
      const channel = await deliverSpokenOperatorAlert({
        eligible: true,
        reason: 'operator_briefing_spoken',
        signal_id: null,
        message: response.line.trim(),
      }, sessionStorage, { dedupe: false, speaker: vaxonVoiceSpeaker() });
      if (channel !== 'skipped') {
        input.briefingVoiceTranscript.value = appendBriefingVoiceTranscriptEntry({
          message: response.line.trim(),
          workspaceId: input.currentWorkspace.value?.workspace_id ?? null,
        });
      }
      scheduleBriefingSurfaceOffer();
    } catch {
      // Voice line unavailable — operator can read briefing in dock.
    }
  }

  async function maybeSpeakBootGreeting(): Promise<void> {
    if (!voiceDeliveryAllowed()) {
      return;
    }
    const greetingKey = 'axon-x:kairo-greeting-spoken';
    if (typeof sessionStorage !== 'undefined' && sessionStorage.getItem(greetingKey) === '1') {
      return;
    }
    if (input.effectiveKairoNarrationLevel.value === 'off' || input.operatorPresenceSettings.value.privacy_mode) {
      return;
    }

    let message = '';
    try {
      const response = await postKairoSpeak({
        event_type: 'greeting',
        context: {
          workspace_count: input.workspaces.value.length,
          pending_approvals: input.pendingApprovalsCount.value,
        },
        session_id: kairoSpeechSessionId(),
        workspace_id: input.currentWorkspace.value?.workspace_id ?? '',
        narration: input.effectiveKairoNarrationLevel.value,
      });
      if (response.source === 'skipped' || !response.line?.trim()) {
        return;
      }
      message = response.line.trim();
    } catch {
      return;
    }

    if (typeof sessionStorage !== 'undefined') {
      sessionStorage.setItem(greetingKey, '1');
    }

    void deliverSpokenOperatorAlert(
      {
        eligible: true,
        reason: 'boot_greeting',
        signal_id: null,
        message,
      },
      sessionStorage,
      { speaker: vaxonVoiceSpeaker() },
    );
  }

  function kairoVoiceContext(): {
    fullAccess: boolean;
    activeFile?: string | null;
  } {
    return {
      fullAccess: input.ideComposerActivity.value?.executionAccess === 'full',
      activeFile: input.activeWorkspaceFilePath.value,
    };
  }


  if (typeof window !== 'undefined') {
    subscribeSpeechQueueSpeaking((active) => {
      input.kairoSpeechQueueActive.value = active;
    });
    subscribeKairoVoiceSpeaking((active) => {
      input.kairoVoiceEngineActive.value = active;
    });
    const finishKairoSpeechPhase = (): void => {
      input.kairoVoicePaused.value = false;
      if (kairoConversationPhase.value === 'speaking' && !isKairoVoiceSpeaking()) {
        setKairoConversationPhase('idle');
      }
    };
    onSpeechQueueIdle(finishKairoSpeechPhase);
    onKairoVoiceIdle(finishKairoSpeechPhase);
  }

  return {
    kairoSpeechSessionId,
    voiceDeliveryAllowed,
    stopKairoSpeech,
    pauseKairoSpeech,
    resumeKairoSpeech,
    interruptKairoVoice,
    speakKairoConversationLine,
    handleKairoPresenceAction,
    deliverKairoSpokenAlert,
    speakOperatorBriefing,
    maybeSpeakBootGreeting,
    kairoVoiceContext,
  };
}
