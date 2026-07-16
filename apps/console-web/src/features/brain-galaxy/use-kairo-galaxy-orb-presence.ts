import { computed, type ComputedRef } from 'vue';

import { resolveKairoPresenceState, type KairoPresenceState } from '../../lib/kairo-presence';
import { formatVoiceGateFeedback } from '../../lib/kairo-voice-gate';
import { useKairoSpeechCapture } from '../kairo-conversation/use-kairo-speech-capture';
import { isKairoConversationBusy } from '../kairo-conversation/kairo-conversation-state';

type PresenceShell = {
  operatorBriefing: {
    pending_approvals: { count: number };
    top_signals: Array<{ severity: string }>;
  } | null;
  runtimeSummary: {
    approvals: { pending_count: number };
    watch: { connected: boolean };
  } | null;
  runtimeSummaryLoadState: string;
  operatorPresenceSettings: {
    hands_free_enabled?: boolean;
    privacy_mode: boolean;
    stt_mode?: string;
  };
  agentStreamActive?: boolean;
};

export function useKairoGalaxyOrbPresence(shell: PresenceShell) {
  const pendingApprovals = computed(
    () =>
      shell.operatorBriefing?.pending_approvals.count ??
      shell.runtimeSummary?.approvals.pending_count ??
      0,
  );
  const handsFreeEnabled = computed(
    () => shell.operatorPresenceSettings.hands_free_enabled === true,
  );
  const presenceState: ComputedRef<KairoPresenceState> = computed(() => {
    const high =
      shell.operatorBriefing?.top_signals.filter((s) => s.severity === 'high').length ?? 0;
    const critical =
      shell.operatorBriefing?.top_signals.filter((s) => s.severity === 'critical').length ?? 0;
    return resolveKairoPresenceState({
      pendingApprovals: pendingApprovals.value,
      criticalSignals: critical,
      highSignals: high,
      watchConnected: shell.runtimeSummary?.watch.connected ?? false,
      runtimeLoaded: shell.runtimeSummaryLoadState === 'loaded',
      privacyBlocked: shell.operatorPresenceSettings.privacy_mode,
    });
  });

  const speechCapture = useKairoSpeechCapture({
    privacyBlocked: () => shell.operatorPresenceSettings.privacy_mode,
    sttMode: () => shell.operatorPresenceSettings.stt_mode ?? 'browser',
    captureMode: 'manual',
    stopOnUnmount: 'manual_only',
  });
  const gateFeedback = computed(() =>
    formatVoiceGateFeedback(
      speechCapture.lastGateReason.value,
      speechCapture.lastHeardTranscript.value,
      speechCapture.lastAccepted.value,
    ),
  );
  const orbBusy = computed(
    () => isKairoConversationBusy() || shell.agentStreamActive === true,
  );
  const voiceBlocked = computed(() => shell.operatorPresenceSettings.privacy_mode);

  return {
    handsFreeEnabled,
    presenceState,
    speechCapture,
    gateFeedback,
    orbBusy,
    voiceBlocked,
  };
}
