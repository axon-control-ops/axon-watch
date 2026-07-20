import { describe, expect, it } from 'vitest';

import {
  buildConnectorRailRows,
  buildConnectorsRailSummaryLabel,
  buildConnectorsRailWatchOfflineBody,
  connectorsRailEmphasized,
  connectorsRailProbeListVisible,
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

  it('hides probe rows when the watch is offline', () => {
    expect(buildConnectorsRailWatchOfflineBody()).toContain('Watch offline');
    expect(
      connectorsRailProbeListVisible({
        loading: false,
        watchConnected: false,
        hasError: false,
      }),
    ).toBe(false);
    expect(
      connectorsRailProbeListVisible({
        loading: false,
        watchConnected: true,
        hasError: false,
      }),
    ).toBe(true);
    expect(
      connectorsRailProbeListVisible({
        loading: true,
        watchConnected: true,
        hasError: false,
      }),
    ).toBe(false);
  });

  it('shows watch offline instead of stale required-down counts', () => {
    expect(
      buildConnectorsRailSummaryLabel({
        loading: false,
        watchConnected: false,
        summary: { configured: 3, ok: 1, required_unavailable: 2 },
      }),
    ).toBe('Watch offline');
    expect(
      connectorsRailEmphasized({
        watchConnected: false,
        summary: { configured: 3, ok: 1, required_unavailable: 2 },
      }),
    ).toBe(false);
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
