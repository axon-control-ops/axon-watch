import { describe, expect, it } from 'vitest';

import { buildConnectorRailRows } from './connector-rail-view';

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
