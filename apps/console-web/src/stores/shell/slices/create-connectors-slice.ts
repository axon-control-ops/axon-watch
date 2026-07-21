import type { Ref } from 'vue';

import {
  fetchConnectors,
  postWatchCommand,
  startTunnel,
  stopTunnel,
  type ConnectorProbeRecord,
} from '../../../api/control-plane';
import { connectorMutationBlockedWhenWatchOffline } from '../../../lib/connector-rail-view';

type ConnectorsLoadState = 'idle' | 'loading' | 'loaded' | 'error';

interface ConnectorsSummary {
  configured: number;
  ok: number;
  degraded: number;
  unavailable: number;
  required_unavailable: number;
}

interface CreateConnectorsSliceInput {
  connectorsItems: Ref<ConnectorProbeRecord[]>;
  connectorsSummary: Ref<ConnectorsSummary | null>;
  connectorsLoadState: Ref<ConnectorsLoadState>;
  connectorsError: Ref<string | null>;
  connectorMutationPending: Ref<boolean>;
  watchConnected: () => boolean;
  loadRuntimeSummary: (options?: { background?: boolean }) => Promise<void>;
  loadInbox: () => Promise<void>;
  loadOperatorBriefing: () => Promise<void>;
  loadOperatorFleetHealth: () => Promise<void>;
}

export function createConnectorsSlice(input: CreateConnectorsSliceInput) {
  let inflightConnectors: Promise<void> | null = null;

  function blockConnectorMutationWhenWatchOffline(): string | null {
    return connectorMutationBlockedWhenWatchOffline(input.watchConnected());
  }

  async function loadConnectors(options?: { background?: boolean }): Promise<void> {
    const hasCached = input.connectorsLoadState.value === 'loaded' && input.connectorsSummary.value;
    const background = options?.background === true || hasCached;

    if (inflightConnectors) {
      return inflightConnectors;
    }

    if (!background) {
      input.connectorsLoadState.value = 'loading';
      input.connectorsError.value = null;
    }

    inflightConnectors = (async () => {
      try {
        const snapshot = await fetchConnectors();
        input.connectorsItems.value = snapshot.items;
        input.connectorsSummary.value = snapshot.summary;
        input.connectorsLoadState.value = 'loaded';
        input.connectorsError.value = null;
      } catch (error) {
        if (!hasCached) {
          input.connectorsLoadState.value = 'error';
          input.connectorsError.value =
            error instanceof Error ? error.message : 'connectors request failed';
        }
      } finally {
        inflightConnectors = null;
      }
    })();

    return inflightConnectors;
  }

  async function reprobeConnector(connectorId: string): Promise<void> {
    const blocked = blockConnectorMutationWhenWatchOffline();
    if (blocked) {
      input.connectorsError.value = blocked;
      return;
    }

    input.connectorMutationPending.value = true;
    input.connectorsError.value = null;

    try {
      await postWatchCommand({
        command_type: 'reprobe_connector',
        target_type: 'connector',
        target_id: connectorId,
        requested_by: 'operator',
      });
      await Promise.all([
        loadConnectors({ background: true }),
        input.loadRuntimeSummary({ background: true }),
        input.loadInbox(),
      ]);
    } catch (error) {
      input.connectorsError.value =
        error instanceof Error ? error.message : 'connector reprobe failed';
    } finally {
      input.connectorMutationPending.value = false;
    }
  }

  async function refreshWatchSummary(): Promise<void> {
    const blocked = blockConnectorMutationWhenWatchOffline();
    if (blocked) {
      input.connectorsError.value = blocked;
      return;
    }

    input.connectorMutationPending.value = true;
    input.connectorsError.value = null;

    try {
      await postWatchCommand({
        command_type: 'refresh_summary',
        requested_by: 'operator',
      });
      await Promise.all([
        loadConnectors({ background: true }),
        input.loadRuntimeSummary({ background: true }),
        input.loadInbox(),
        input.loadOperatorBriefing(),
        input.loadOperatorFleetHealth(),
      ]);
    } catch (error) {
      input.connectorsError.value =
        error instanceof Error ? error.message : 'watch summary refresh failed';
    } finally {
      input.connectorMutationPending.value = false;
    }
  }

  async function startCloudflareTunnel(): Promise<void> {
    const blocked = blockConnectorMutationWhenWatchOffline();
    if (blocked) {
      input.connectorsError.value = blocked;
      return;
    }

    input.connectorMutationPending.value = true;
    input.connectorsError.value = null;

    try {
      await startTunnel();
      await Promise.all([
        loadConnectors({ background: true }),
        input.loadRuntimeSummary({ background: true }),
        input.loadInbox(),
      ]);
    } catch (error) {
      input.connectorsError.value =
        error instanceof Error ? error.message : 'tunnel start failed';
    } finally {
      input.connectorMutationPending.value = false;
    }
  }

  async function stopCloudflareTunnel(): Promise<void> {
    const blocked = blockConnectorMutationWhenWatchOffline();
    if (blocked) {
      input.connectorsError.value = blocked;
      return;
    }

    input.connectorMutationPending.value = true;
    input.connectorsError.value = null;

    try {
      await stopTunnel();
      await Promise.all([
        loadConnectors({ background: true }),
        input.loadRuntimeSummary({ background: true }),
        input.loadInbox(),
      ]);
    } catch (error) {
      input.connectorsError.value =
        error instanceof Error ? error.message : 'tunnel stop failed';
    } finally {
      input.connectorMutationPending.value = false;
    }
  }

  return {
    loadConnectors,
    refreshWatchSummary,
    reprobeConnector,
    startCloudflareTunnel,
    stopCloudflareTunnel,
  };
}
