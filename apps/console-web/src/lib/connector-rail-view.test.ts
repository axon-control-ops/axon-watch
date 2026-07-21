import { describe, expect, it } from 'vitest';

import {
  buildConnectorRailRows,
  buildConnectorRailSummaryLabel,
  buildConnectorRailWatchOfflineStatus,
  connectorMutationBlockedWhenWatchOffline,
  connectorRailNeedsEmphasis,
} from './connector-rail-view';

describe('buildConnectorRailRows', () => {
  it('only marks an Axon-X-owned tunnel as managed', () => {
    const [row] = buildConnectorRailRows([
      {
        connector_id: 'cloudflare_tunnel',
        display_name: 'Cloudflare tunnel',
        status: 'degraded',
        required: false,
        tunnel: {
          process_running: true,
          managed_process: false,
          auth_ready: true,
        },
      },
    ]);

    expect(row.tunnelRunning).toBe(true);
    expect(row.tunnelManaged).toBe(false);
    expect(row.tunnelStartAllowed).toBe(false);
  });

  it('passes through probe failure detail for operator visibility', () => {
    const [row] = buildConnectorRailRows([
      {
        connector_id: 'console_web',
        display_name: 'Console web',
        status: 'unavailable',
        required: true,
        detail: 'Connection refused on http://127.0.0.1:4173/api/health',
      },
    ]);

    expect(row.detail).toBe('Connection refused on http://127.0.0.1:4173/api/health');
    expect(row.tone).toBe('unavailable');
    expect(row.required).toBe(true);
  });
});

describe('buildConnectorRailSummaryLabel', () => {
  const summary = { configured: 3, ok: 2, required_unavailable: 1 };

  it('shows loading copy while probes refresh', () => {
    expect(
      buildConnectorRailSummaryLabel({ loading: true, summary, watchConnected: true }),
    ).toBe('Loading…');
  });

  it('pauses counts when watch is offline', () => {
    expect(
      buildConnectorRailSummaryLabel({ loading: false, summary, watchConnected: false }),
    ).toBe('Watch offline — probe counts paused');
  });

  it('uses effective required-down counts when watch is connected', () => {
    expect(
      buildConnectorRailSummaryLabel({ loading: false, summary, watchConnected: true }),
    ).toBe('2/3 ok · 1 required down');
  });

  it('reports unavailable when probe summary is missing', () => {
    expect(
      buildConnectorRailSummaryLabel({ loading: false, summary: null, watchConnected: true }),
    ).toBe('Connectors unavailable');
  });
});

describe('buildConnectorRailWatchOfflineStatus', () => {
  it('returns offline guidance when watch is disconnected', () => {
    expect(buildConnectorRailWatchOfflineStatus(false)).toContain('Watch offline');
    expect(buildConnectorRailWatchOfflineStatus(true)).toBeNull();
  });
});

describe('connectorMutationBlockedWhenWatchOffline', () => {
  it('blocks watch commands when the lane is disconnected', () => {
    expect(connectorMutationBlockedWhenWatchOffline(false)).toContain('commands paused');
    expect(connectorMutationBlockedWhenWatchOffline(true)).toBeNull();
  });
});

describe('connectorRailNeedsEmphasis', () => {
  it('suppresses emphasis when watch is offline', () => {
    expect(
      connectorRailNeedsEmphasis({
        summary: { configured: 3, ok: 1, required_unavailable: 2 },
        watchConnected: false,
      }),
    ).toBe(false);
  });

  it('emphasizes when required connectors are down', () => {
    expect(
      connectorRailNeedsEmphasis({
        summary: { configured: 3, ok: 1, required_unavailable: 2 },
        watchConnected: true,
      }),
    ).toBe(true);
  });
});
