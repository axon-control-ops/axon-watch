import { computed, onMounted, onUnmounted, ref, watch, type Ref } from 'vue';

import { fetchWorkspaceAgents } from '../../api/workspace-api';
import type { WorkspaceAgentRecord } from '../../contracts/canonical';
import { axonDebugSessionLog } from '../../lib/axon-debug-session-log';

const AGENT_STATUS_REFRESH_MS = 12_000;

export function useWorkspaceAgents(currentWorkspaceId: Ref<string | null | undefined>) {
  const agentsByWorkspaceId = ref<Record<string, WorkspaceAgentRecord>>({});
  const loadState = ref<'idle' | 'loading' | 'loaded' | 'error'>('idle');
  const loadError = ref<string | null>(null);
  let refreshTimer: ReturnType<typeof setInterval> | null = null;

  const currentWorkspaceAgent = computed(() => {
    const workspaceId = currentWorkspaceId.value?.trim();
    if (!workspaceId) {
      return null;
    }
    return agentsByWorkspaceId.value[workspaceId] ?? null;
  });

  async function loadWorkspaceAgents(options?: { reason?: string }): Promise<void> {
    loadState.value = 'loading';
    loadError.value = null;
    try {
      const snapshot = await fetchWorkspaceAgents({ scope: 'operator' });
      const next: Record<string, WorkspaceAgentRecord> = {};
      for (const agent of snapshot.items) {
        next[agent.workspace_id] = agent;
      }
      agentsByWorkspaceId.value = next;
      loadState.value = 'loaded';
      // #region agent log
      axonDebugSessionLog({
        hypothesisId: 'EA4',
        location: 'use-workspace-agents.ts:loadWorkspaceAgents',
        message: 'employee agents snapshot loaded into UI cache',
        data: {
          count: snapshot.items.length,
          statuses: Object.fromEntries(
            snapshot.items.map((agent) => [agent.workspace_id, agent.status]),
          ),
          reason: options?.reason ?? 'unspecified',
          cacheOnlyUntilRemount: false,
        },
        workspaceId: 'workspace_axon_watch',
      });
      // #endregion
    } catch (error) {
      loadState.value = 'error';
      loadError.value = error instanceof Error ? error.message : 'workspace agents request failed';
    }
  }

  function agentForWorkspace(workspaceId: string): WorkspaceAgentRecord | null {
    return agentsByWorkspaceId.value[workspaceId] ?? null;
  }

  onMounted(() => {
    void loadWorkspaceAgents({ reason: 'mount' });
    refreshTimer = setInterval(() => {
      void loadWorkspaceAgents({ reason: 'interval' });
    }, AGENT_STATUS_REFRESH_MS);
  });

  onUnmounted(() => {
    if (refreshTimer !== null) {
      clearInterval(refreshTimer);
      refreshTimer = null;
    }
  });

  watch(currentWorkspaceId, (workspaceId) => {
    if (!workspaceId) {
      return;
    }
    void loadWorkspaceAgents({ reason: 'workspace-change' });
  });

  return {
    agentsByWorkspaceId,
    currentWorkspaceAgent,
    loadState,
    loadError,
    loadWorkspaceAgents,
    agentForWorkspace,
  };
}
