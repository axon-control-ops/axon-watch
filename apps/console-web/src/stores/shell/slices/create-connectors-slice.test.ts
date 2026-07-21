import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ref, type Ref } from 'vue';

vi.mock('../../../api/control-plane', () => ({
  fetchConnectors: vi.fn(),
  postWatchCommand: vi.fn(),
  startTunnel: vi.fn(),
  stopTunnel: vi.fn(),
}));

import {
  fetchConnectors,
  postWatchCommand,
  startTunnel,
  stopTunnel,
  type ConnectorProbeRecord,
} from '../../../api/control-plane';
import { createConnectorsSlice } from './create-connectors-slice';

const OFFLINE_COPY =
  'Watch offline — connector commands paused until the watch reconnects.';

type ConnectorsLoadState = 'idle' | 'loading' | 'loaded' | 'error';
type ConnectorsSummary = {
  configured: number;
  ok: number;
  degraded: number;
  unavailable: number;
  required_unavailable: number;
};

describe('createConnectorsSlice watch-offline guard', () => {
  const fetchConnectorsMock = vi.mocked(fetchConnectors);
  const postWatchCommandMock = vi.mocked(postWatchCommand);
  const startTunnelMock = vi.mocked(startTunnel);
  const stopTunnelMock = vi.mocked(stopTunnel);

  let connectorsItems: Ref<ConnectorProbeRecord[]>;
  let connectorsSummary: Ref<ConnectorsSummary | null>;
  let connectorsLoadState: Ref<ConnectorsLoadState>;
  let connectorsError: Ref<string | null>;
  let connectorMutationPending: Ref<boolean>;
  let watchConnected: () => boolean;

  function createSlice() {
    return createConnectorsSlice({
      connectorsItems,
      connectorsSummary,
      connectorsLoadState,
      connectorsError,
      connectorMutationPending,
      watchConnected,
      loadRuntimeSummary: vi.fn().mockResolvedValue(undefined),
      loadInbox: vi.fn().mockResolvedValue(undefined),
      loadOperatorBriefing: vi.fn().mockResolvedValue(undefined),
      loadOperatorFleetHealth: vi.fn().mockResolvedValue(undefined),
    });
  }

  beforeEach(() => {
    vi.clearAllMocks();
    connectorsItems = ref<ConnectorProbeRecord[]>([]);
    connectorsSummary = ref<ConnectorsSummary | null>(null);
    connectorsLoadState = ref<ConnectorsLoadState>('idle');
    connectorsError = ref<string | null>(null);
    connectorMutationPending = ref(false);
    watchConnected = () => false;
  });

  it('blocks reprobe when watch is offline', async () => {
    const slice = createSlice();

    await slice.reprobeConnector('control_plane');

    expect(connectorsError.value).toBe(OFFLINE_COPY);
    expect(postWatchCommandMock).not.toHaveBeenCalled();
    expect(connectorMutationPending.value).toBe(false);
  });

  it('blocks refresh summary when watch is offline', async () => {
    const slice = createSlice();

    await slice.refreshWatchSummary();

    expect(connectorsError.value).toBe(OFFLINE_COPY);
    expect(postWatchCommandMock).not.toHaveBeenCalled();
    expect(connectorMutationPending.value).toBe(false);
  });

  it('blocks tunnel start and stop when watch is offline', async () => {
    const slice = createSlice();

    await slice.startCloudflareTunnel();
    expect(connectorsError.value).toBe(OFFLINE_COPY);
    expect(startTunnelMock).not.toHaveBeenCalled();

    connectorsError.value = null;
    await slice.stopCloudflareTunnel();
    expect(connectorsError.value).toBe(OFFLINE_COPY);
    expect(stopTunnelMock).not.toHaveBeenCalled();
  });

  it('runs reprobe when watch is connected', async () => {
    watchConnected = () => true;
    fetchConnectorsMock.mockResolvedValue({
      count: 0,
      items: [],
      summary: {
        configured: 0,
        ok: 0,
        degraded: 0,
        unavailable: 0,
        required_unavailable: 0,
      },
    });
    postWatchCommandMock.mockResolvedValue({
      command_id: 'cmd_test',
      status: 'completed',
    });

    const slice = createSlice();
    await slice.reprobeConnector('console_web');

    expect(postWatchCommandMock).toHaveBeenCalledWith({
      command_type: 'reprobe_connector',
      target_type: 'connector',
      target_id: 'console_web',
      requested_by: 'operator',
    });
    expect(connectorsError.value).toBeNull();
    expect(fetchConnectorsMock).toHaveBeenCalled();
  });
});
