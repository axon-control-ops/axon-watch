import { computed, onMounted, onUnmounted, ref } from 'vue';

import {
  fetchAutonomyStatus,
  type AutonomyReceipt,
} from '../api/autonomy-api';
import {
  kairoConversationPhase,
  kairoLastRoutingReceipt,
} from '../features/kairo-conversation/kairo-conversation-state';
import { resolveGalaxyPresence } from '../features/brain-galaxy/galaxy-presence-state';
import { projectLiveOperationsStream } from '../features/brain-galaxy/live-operations-stream';
import { companyBusyEmployeesCount } from '../features/workspace-agents/company-roster-busy';
import { useShellStore } from '../stores/shell';

const autonomyReceipts = ref<AutonomyReceipt[]>([]);
const autonomyEffective = ref(false);
let autonomyPoll: ReturnType<typeof setInterval> | null = null;
let presenceMountCount = 0;

async function refreshAutonomyReceipts(shell: ReturnType<typeof useShellStore>): Promise<void> {
  try {
    const workspaceId = shell.currentWorkspace?.workspace_id?.trim();
    const feed = await fetchAutonomyStatus(workspaceId);
    if (feed.autonomy_mode !== shell.operatorPresenceSettings.autonomy_mode) {
      await shell.loadOperatorPresenceSettings({ reportError: false });
    }
    autonomyReceipts.value = feed.recent_receipts ?? [];
    autonomyEffective.value =
      feed.effective_autonomy &&
      feed.autonomy_mode === shell.operatorPresenceSettings.autonomy_mode;
  } catch {
    // Keep last good receipts; stream falls back to briefing items.
  }
}

function startAutonomyPoll(shell: ReturnType<typeof useShellStore>): void {
  if (autonomyPoll !== null) {
    return;
  }
  void refreshAutonomyReceipts(shell);
  autonomyPoll = setInterval(() => {
    void refreshAutonomyReceipts(shell);
  }, 10_000);
}

function stopAutonomyPoll(): void {
  if (autonomyPoll === null) {
    return;
  }
  clearInterval(autonomyPoll);
  autonomyPoll = null;
}

export function useMcVaxonPresence() {
  const shell = useShellStore();

  const companyBusyCount = computed(() =>
    companyBusyEmployeesCount(shell.companyEmployeesFleet),
  );

  const fleetActiveRuns = computed(
    () =>
      shell.runtimeSummary?.active_runs?.length ??
      shell.operatorBriefing?.active_runs?.length ??
      0,
  );

  const autonomyMode = computed(
    () => shell.operatorPresenceSettings.autonomy_mode ?? 'manual',
  );

  const fullAutonomyActive = computed(
    () => autonomyMode.value === 'full' && autonomyEffective.value,
  );

  const presence = computed(() =>
    resolveGalaxyPresence({
      selectedNodeId: null,
      selectedNodeKind: null,
      conversationPhase: kairoConversationPhase.value,
      speechCapturing: false,
      kairoSpeechActive: shell.kairoSpeechActive,
      agentStreamActive: shell.agentStreamActive,
      companyBusyCount: companyBusyCount.value,
      fleetActiveRuns: fleetActiveRuns.value,
      pendingApprovals:
        shell.runtimeSummary?.approvals.pending_count ??
        shell.operatorBriefing?.pending_approvals.count ??
        0,
      criticalSignals: shell.runtimeSummary?.signals.critical_count ?? 0,
      highSignals: shell.runtimeSummary?.signals.high_count ?? 0,
      openSignals: shell.runtimeSummary?.signals.open_count ?? 0,
      fullAutonomyActive: fullAutonomyActive.value,
    }),
  );

  const presencePhase = computed(() => presence.value.phase);

  const streamItems = computed(() =>
    projectLiveOperationsStream({
      briefing: shell.operatorBriefing,
      primaryActiveRun: shell.primaryActiveRun,
      employees: shell.companyEmployeesForCurrentWorkspace,
      presencePhase: presencePhase.value,
      routingReceipt: kairoLastRoutingReceipt.value,
      degradedReasons: [],
      autonomyReceipts: autonomyReceipts.value,
      autonomyMode: autonomyMode.value,
    }),
  );

  const modeChip = computed(() => {
    if (presencePhase.value === 'speaking') return 'speaking';
    if (presencePhase.value === 'listening') return 'listening';
    if (presencePhase.value === 'autonomous' || fullAutonomyActive.value) return 'autonomous';
    if (presencePhase.value === 'alerting') return 'scanning';
    return 'standby';
  });

  const liveBadge = computed(
    () =>
      shell.kairoSpeechActive ||
      presencePhase.value === 'listening' ||
      presencePhase.value === 'speaking' ||
      presencePhase.value === 'thinking' ||
      presencePhase.value === 'autonomous' ||
      presencePhase.value === 'alerting' ||
      fullAutonomyActive.value ||
      Boolean(shell.primaryActiveRun) ||
      companyBusyCount.value > 0 ||
      fleetActiveRuns.value > 0,
  );

  onMounted(() => {
    presenceMountCount += 1;
    if (presenceMountCount === 1) {
      startAutonomyPoll(shell);
    }
  });

  onUnmounted(() => {
    presenceMountCount = Math.max(0, presenceMountCount - 1);
    if (presenceMountCount === 0) {
      stopAutonomyPoll();
    }
  });

  return {
    autonomyMode,
    companyBusyCount,
    fleetActiveRuns,
    fullAutonomyActive,
    liveBadge,
    modeChip,
    presencePhase,
    streamItems,
  };
}
