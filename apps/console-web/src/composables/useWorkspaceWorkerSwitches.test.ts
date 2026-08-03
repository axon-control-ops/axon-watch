import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../api/worker-scheduler-api', () => ({
  fetchWorkerSchedulerStatus: vi.fn(async () => ({
    workspace_enabled: { workspace_bkk_invoice_system: false },
  })),
  patchWorkspaceWorkerEnabled: vi.fn(async (_id: string, enabled: boolean) => ({
    workspace_id: 'workspace_bkk_invoice_system',
    enabled,
    workspace_enabled: { workspace_bkk_invoice_system: enabled },
  })),
}));

import { patchWorkspaceWorkerEnabled } from '../api/worker-scheduler-api';
import { useWorkspaceWorkerSwitches } from './useWorkspaceWorkerSwitches';

describe('useWorkspaceWorkerSwitches', () => {
  beforeEach(() => vi.clearAllMocks());

  it('defaults absent workspace switches to on and loads persisted pauses', async () => {
    const switches = useWorkspaceWorkerSwitches({ autoLoad: false, pollMs: 0 });
    await switches.reloadWorkspaceSwitches();

    expect(switches.isWorkspaceWorkerOn('workspace_dashpro')).toBe(true);
    expect(switches.isWorkspaceWorkerOn('workspace_bkk_invoice_system')).toBe(false);
  });

  it('persists an optimistic workspace switch update', async () => {
    const switches = useWorkspaceWorkerSwitches({ autoLoad: false, pollMs: 0 });
    await switches.reloadWorkspaceSwitches();

    await expect(
      switches.setWorkspaceWorkerOn('workspace_bkk_invoice_system', true),
    ).resolves.toBe(true);
    expect(patchWorkspaceWorkerEnabled).toHaveBeenCalledWith(
      'workspace_bkk_invoice_system',
      true,
    );
    expect(switches.isWorkspaceWorkerOn('workspace_bkk_invoice_system')).toBe(true);
  });
});
