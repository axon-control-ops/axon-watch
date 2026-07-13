import { computed, onMounted, ref, watch, type Ref } from 'vue';

import { fetchWorkspaceAgents } from '../../api/workspace-api';
import type { WorkspaceAgentRecord } from '../../contracts/canonical';

export function useWorkspaceAgents(currentWorkspaceId: Ref<string | null | undefined>) {
  const agentsByWorkspaceId = ref<Record<string, WorkspaceAgentRecord>>({});
  const loadState = ref<'idle' | 'loading' | 'loaded' | 'error'>('idle');
  const loadError = ref<string | null>(null);

  const currentWorkspaceAgent = computed(() => {
    const workspaceId = currentWorkspaceId.value?.trim();
    if (!workspaceId) {
      return null;
    }
    return agentsByWorkspaceId.value[workspaceId] ?? null;
  });

  async function loadWorkspaceAgents(): Promise<void> {
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
    } catch (error) {
      loadState.value = 'error';
      loadError.value = error instanceof Error ? error.message : 'workspace agents request failed';
    }
  }

  function agentForWorkspace(workspaceId: string): WorkspaceAgentRecord | null {
    return agentsByWorkspaceId.value[workspaceId] ?? null;
  }

  onMounted(() => {
    if (loadState.value === 'idle') {
      void loadWorkspaceAgents();
    }
  });

  watch(currentWorkspaceId, (workspaceId) => {
    if (!workspaceId || agentsByWorkspaceId.value[workspaceId]) {
      return;
    }
    if (loadState.value === 'loaded') {
      void loadWorkspaceAgents();
    }
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
