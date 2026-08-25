import { computed, onUnmounted, ref } from 'vue';

import {
  listSandboxPreviews,
  stopSandboxPreviewPort,
  type SandboxPreviewProcess,
} from '../api/composer-sandbox-api';

const POLL_INTERVAL_MS = 10_000;

/**
 * Running sandbox preview servers, for the status bar.
 *
 * Polls rather than relying on the in-memory registry alone: a preview can
 * outlive a control-plane restart, and an orphan holding a port with nothing
 * in the UI to show or reclaim it is the exact failure this surface exists to
 * prevent.
 */
export function useSandboxPreviewServers(workspaceId: () => string | undefined) {
  const servers = ref<SandboxPreviewProcess[]>([]);
  const error = ref('');
  const pending = ref(false);
  const panelOpen = ref(false);

  const count = computed(() => servers.value.length);
  const hasServers = computed(() => count.value > 0);

  async function refresh(): Promise<void> {
    const id = workspaceId();
    if (!id) {
      servers.value = [];
      return;
    }
    try {
      const response = await listSandboxPreviews(id);
      // Discard a response that lost its race with a workspace switch.
      if (workspaceId() !== id) return;
      servers.value = response.items ?? [];
      error.value = '';
    } catch (caught) {
      servers.value = [];
      error.value = caught instanceof Error ? caught.message : 'Could not list preview servers.';
    }
  }

  async function stop(port: number): Promise<void> {
    const id = workspaceId();
    if (!id || pending.value) return;
    pending.value = true;
    try {
      const result = await stopSandboxPreviewPort(id, port);
      error.value = result.stopped
        ? `Stopped preview on port ${port}.`
        : `Nothing was listening on port ${port}.`;
      await refresh();
    } catch (caught) {
      error.value = caught instanceof Error ? caught.message : `Could not stop port ${port}.`;
    } finally {
      pending.value = false;
    }
  }

  async function stopAll(): Promise<void> {
    for (const server of [...servers.value]) {
      await stop(server.port);
    }
  }

  function togglePanel(): void {
    panelOpen.value = !panelOpen.value;
    if (panelOpen.value) void refresh();
  }

  const timer = window.setInterval(() => void refresh(), POLL_INTERVAL_MS);
  onUnmounted(() => window.clearInterval(timer));
  void refresh();

  return { servers, count, hasServers, error, pending, panelOpen, refresh, stop, stopAll, togglePanel };
}
