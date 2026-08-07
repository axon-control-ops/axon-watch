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
import { unlockKairoAudioPlayback } from '../../../lib/kairo-audio-unlock';
import { deliverSpokenOperatorAlert } from '../../../lib/spoken-alert-delivery';
import {
  type KairoVoiceSpeaker,
  vaxonVoiceSpeaker,
} from '../../../lib/kairo-voice-utterance';
import { buildKairoSpeechSessionId } from '../../../lib/kairo-speech-session';
import { ideVoiceSpeechAllowed } from '../../../lib/ide-voice-strip';
import { postKairoSpeak } from '../../../lib/kairo-speak-client';
import type { LiveEventPayload } from '../../../lib/live-events-session';
import {
  onKairoVoiceIdle,
  pauseKairoPlayback,
  resumeKairoPlayback,
  speakKairoLine,
  stopKairoPlayback,
  subscribeKairoVoiceSpeaking,
  isKairoVoiceSpeaking,
} from '../../../lib/kairo-voice-playback';
import { reportTheaterOpen } from '../../../features/report-theater/report-theater-state';
import { isReportTheaterAutoStartPending } from '../../../features/report-theater/report-theater-auto-start';
import { navigateToAppSurface } from '../../../lib/app-surface-route';
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
import { speakSpokenLineEvent } from './kairo-voice-spoken-line';

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
  focusCommandSeam?: () => void;
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
    if (typeof document !== 'undefined' && document.visibilityState === 'hidden') {
      // #region agent log
      fetch('http://127.0.0.1:7706/ingest/90bcaec2-2b39-4d4a-84b5-157c12735440', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Debug-Session-Id': '9e41d8' },
        body: JSON.stringify({
          sessionId: '9e41d8',
          runId: 'post-fix',
          hypothesisId: 'H6_cross_context',
          location: 'create-kairo-voice-slice.ts:voiceDeliveryAllowed',
          message: 'voice delivery rejected for hidden document',
          data: { documentVisibility: document.visibilityState },
          timestamp: Date.now(),
        }),
      }).catch(() => {});
      // #endregion agent log
      return false;
    }
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
    void interruptKairoVoiceAndWait();
  }

  async function interruptKairoVoiceAndWait(): Promise<void> {
    await interruptKairoSpeechQueue('barge_in');
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
      priority?: 'interrupt' | 'alert' | 'conversation' | 'narration';
      allowDuringReportTheater?: boolean;
      ttsTimeoutMs?: number;
      onPlaybackStart?: () => void;
    },
  ): Promise<void> {
    const trimmed = line.trim();
    const configuredNarration = input.operatorPresenceSettings.value.kairo_narration ?? 'minimal';
    // #region agent log
    fetch('http://127.0.0.1:7706/ingest/90bcaec2-2b39-4d4a-84b5-157c12735440', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Debug-Session-Id': '9e41d8' },
      body: JSON.stringify({
        sessionId: '9e41d8',
        hypothesisId: 'H4_conversation_channel',
        location: 'create-kairo-voice-slice.ts:speakKairoConversationLine',
        message: 'conversation-channel speech requested',
        data: {
          priority: options?.priority ?? 'conversation',
          speakerId: options?.speaker?.id ?? null,
          operatorPrompt: options?.operatorPrompt?.slice(0, 80) ?? '',
          textPreview: trimmed.slice(0, 180),
          skipSpeakApi: options?.skipSpeakApi === true,
          documentVisibility:
            typeof document === 'undefined' ? null : document.visibilityState,
        },
        timestamp: Date.now(),
      }),
    }).catch(() => {});
    // #endregion agent log
    if (
      !trimmed ||
      !voiceDeliveryAllowed() ||
      input.operatorPresenceSettings.value.privacy_mode ||
      configuredNarration === 'off'
    ) {
      options?.onPlaybackStart?.();
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
      priority: options?.priority ?? 'conversation',
      speechRate: input.operatorPresenceSettings.value.speech_rate,
      speechPitch: input.operatorPresenceSettings.value.speech_pitch,
      azureVoiceId: options?.azureVoiceId?.trim() || undefined,
      speaker,
      allowDuringReportTheater: options?.allowDuringReportTheater === true,
      ttsTimeoutMs: options?.ttsTimeoutMs,
      onPlaybackStart: options?.onPlaybackStart,
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
    // Command theater owns the voice queue — do not barge in with alerts/advisories.
    if (reportTheaterOpen.value) {
      return;
    }
    // Full autonomy just kicked off REPORT — let theater speak and act instead of a passive brief.
    if (alert.reason === 'autonomy_advisory' && isReportTheaterAutoStartPending()) {
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
    const strippedAlertMessage = alert.message
      .replace(/^(?:VAXON|NAXON|X|KAIRO):\s*/i, '')
      .trim();
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

    // Speak control-plane crafted copy literally — do not rebuild idle persona filler.
    if (
      alert.reason === 'operator_approval_required' ||
      alert.reason === 'autonomy_advisory'
    ) {
      eventType = 'approval_literal';
      context.literal_line = strippedAlertMessage;
    }

    let message = '';
    let speakSource = '';
    try {
      const response = await postKairoSpeak({
        event_type: eventType,
        context,
        session_id: kairoSpeechSessionId(),
        workspace_id: input.currentWorkspace.value?.workspace_id ?? '',
        narration: input.effectiveKairoNarrationLevel.value,
        use_runtime: eventType !== 'approval_literal',
      });
      if (response.source === 'skipped' || !response.line?.trim()) {
        return;
      }
      message = response.line.trim();
      speakSource = response.source;
    } catch {
      return;
    }

    // Drop in-flight alerts that started before Command Theater opened.
    if (reportTheaterOpen.value) {
      return;
    }

    await deliverSpokenOperatorAlert(
      {
        eligible: true,
        reason: alert.reason,
        signal_id: alert.signal_id,
        message,
      },
      sessionStorage,
      { speaker: vaxonVoiceSpeaker() },
    );

    // Full autonomy fallback: after "walk the fix", open Vault / command seam automatically.
    if (
      alert.reason === 'runtime_degraded' &&
      input.operatorPresenceSettings.value.autonomy_mode === 'full' &&
      !reportTheaterOpen.value
    ) {
      const blockers = input.operatorBriefing.value?.production_readiness?.blockers ?? [];
      const hay = blockers.join(' ').toLowerCase();
      const preferVault = /vault|cli|auth|key|login|dispatch-ready|runtime not ready/i.test(hay) ||
        /vault|cli|runtime/i.test(message);
      if (preferVault) {
        navigateToAppSurface('vault');
      } else {
        input.focusCommandSeam?.();
      }
    }
  }

  async function speakSpokenLine(event: LiveEventPayload): Promise<void> {
    await speakSpokenLineEvent({
      event,
      voiceDeliveryAllowed,
      privacyMode: input.operatorPresenceSettings.value.privacy_mode,
      spokenAlertsEnabled: input.operatorPresenceSettings.value.spoken_alerts_enabled,
      narrationLevel: input.effectiveKairoNarrationLevel.value,
      currentWorkspace: input.currentWorkspace.value,
      sessionStorage,
    });
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

    // Same gesture unlocks WebKit/Tauri audio so we do not queue silently.
    await unlockKairoAudioPlayback();

    try {
      // Explicit Speak briefing should be snappy: use deterministic notice/advise
      // copy instead of waiting on the Cursor runtime paraphrase path.
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
        use_runtime: false,
      });
      if (response.source === 'skipped' || !response.line?.trim()) {
        return;
      }
      const channel = await deliverSpokenOperatorAlert(
        {
          eligible: true,
          reason: 'operator_briefing_spoken',
          signal_id: null,
          message: response.line.trim(),
        },
        sessionStorage,
        {
          dedupe: false,
          speaker: vaxonVoiceSpeaker(),
          queueUntilUnlock: false,
        },
      );
      if (channel !== 'skipped') {
        input.briefingVoiceTranscript.value = appendBriefingVoiceTranscriptEntry({
          message: response.line.trim(),
          workspaceId: input.currentWorkspace.value?.workspace_id ?? null,
        });
      }
      if (!reportTheaterOpen.value) {
        scheduleBriefingSurfaceOffer();
      }
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
    interruptKairoVoiceAndWait,
    speakKairoConversationLine,
    handleKairoPresenceAction,
    deliverKairoSpokenAlert,
    speakSpokenLine,
    speakOperatorBriefing,
    maybeSpeakBootGreeting,
    kairoVoiceContext,
  };
}
