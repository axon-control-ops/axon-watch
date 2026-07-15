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
});
