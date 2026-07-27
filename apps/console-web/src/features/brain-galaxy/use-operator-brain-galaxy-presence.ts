import { computed, type ComputedRef } from 'vue';

import { companyBusyEmployeesCount } from '../workspace-agents/company-roster-busy';
import type { useShellStore } from '../../stores/shell';

type ShellStore = ReturnType<typeof useShellStore>;

/** Presence inputs shared by the brain galaxy stage. */
export function useOperatorBrainGalaxyPresence(shell: ShellStore): {
  pendingApprovals: ComputedRef<number>;
  criticalSignals: ComputedRef<number>;
  highSignals: ComputedRef<number>;
  kairoSpeechActive: ComputedRef<boolean>;
  agentStreamActive: ComputedRef<boolean>;
  companyBusyCount: ComputedRef<number>;
  fleetActiveRuns: ComputedRef<number>;
  streamWorkspaceId: ComputedRef<string | null>;
} {
  const pendingApprovals = computed(
    () =>
      shell.operatorBriefing?.pending_approvals.count ??
      shell.runtimeSummary?.approvals.pending_count ??
      0,
  );
  const criticalSignals = computed(
    () =>
      shell.operatorBriefing?.top_signals.filter((signal) => signal.severity === 'critical')
        .length ?? 0,
  );
  const highSignals = computed(
    () =>
      shell.operatorBriefing?.top_signals.filter((signal) => signal.severity === 'high').length ??
      0,
  );
  const kairoSpeechActive = computed(() => shell.kairoSpeechActive);
  const agentStreamActive = computed(() => shell.agentStreamActive);
  const companyBusyCount = computed(() =>
    companyBusyEmployeesCount(shell.companyEmployeesFleet),
  );
  const fleetActiveRuns = computed(
    () =>
      shell.runtimeSummary?.active_runs?.length ??
      shell.operatorBriefing?.active_runs?.length ??
      0,
  );
  const streamWorkspaceId = computed(() => shell.currentWorkspace?.workspace_id ?? null);

  return {
    pendingApprovals,
    criticalSignals,
    highSignals,
    kairoSpeechActive,
    agentStreamActive,
    companyBusyCount,
    fleetActiveRuns,
    streamWorkspaceId,
  };
}
