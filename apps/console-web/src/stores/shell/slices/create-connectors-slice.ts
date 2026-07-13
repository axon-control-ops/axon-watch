import type { Ref } from 'vue';

import {
  fetchConnectors,
  postWatchCommand,
  startTunnel,
  stopTunnel,
  type ConnectorProbeRecord,
} from '../../../api/control-plane';

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
  loadRuntimeSummary: () => Promise<void>;
  loadInbox: () => Promise<void>;
  loadOperatorBriefing: () => Promise<void>;
  loadOperatorFleetHealth: () => Promise<void>;
}

export function createConnectorsSlice(input: CreateConnectorsSliceInput) {
  async function loadConnectors(): Promise<void> {
    input.connectorsLoadState.value = 'loading';
    input.connectorsError.value = null;

    try {
      const snapshot = await fetchConnectors();
      input.connectorsItems.value = snapshot.items;
      input.connectorsSummary.value = snapshot.summary;
      input.connectorsLoadState.value = 'loaded';
      // #region agent log
      void import('../../../lib/axon-debug-session-log').then(({ axonDebugSessionLog }) => {
        const unavailable = snapshot.items.filter((item) => item.status === 'unavailable');
        const axonLocal = snapshot.items.find((item) => item.connector_id === 'axon_local');
        axonDebugSessionLog({
          hypothesisId: 'H2',
          location: 'create-connectors-slice.ts:loadConnectors',
          message: 'connectors snapshot loaded',
          data: {
            summary: snapshot.summary,
            unavailableIds: unavailable.map((item) => item.connector_id),
            axonLocalStatus: axonLocal?.status ?? null,
            axonLocalDetail: axonLocal?.detail ?? null,
          },
        });
      });
      // #endregion
    } catch (error) {
      input.connectorsLoadState.value = 'error';
      input.connectorsError.value =
        error instanceof Error ? error.message : 'connectors request failed';
    }
  }

  async function reprobeConnector(connectorId: string): Promise<void> {
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
        loadConnectors(),
        input.loadRuntimeSummary(),
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
    input.connectorMutationPending.value = true;
    input.connectorsError.value = null;

    try {
      await postWatchCommand({
        command_type: 'refresh_summary',
        requested_by: 'operator',
      });
      await Promise.all([
        loadConnectors(),
        input.loadRuntimeSummary(),
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
    input.connectorMutationPending.value = true;
    input.connectorsError.value = null;

    try {
      await startTunnel();
      await Promise.all([
        loadConnectors(),
        input.loadRuntimeSummary(),
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
    input.connectorMutationPending.value = true;
    input.connectorsError.value = null;

    try {
      await stopTunnel();
      await Promise.all([
        loadConnectors(),
        input.loadRuntimeSummary(),
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
