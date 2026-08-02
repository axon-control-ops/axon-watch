import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../api/worker-scheduler-api', () => ({
  fetchWorkerSchedulerStatus: vi.fn(async () => ({
    scheduler_enabled: false,
    effective_enabled: false,
    env_allowed: true,
    blocked_by_env: false,
    max_active: 4,
    max_starts_per_tick: 2,
    tick_interval_seconds: 30,
    dispatch_enabled: true,
    executing_count: 0,
    active_run_count: 0,
    employee_enabled: {},
    workspace_enabled: {
      workspace_bkk_invoice_system: false,
    },
  })),
  patchWorkspaceWorkerEnabled: vi.fn(async (_id: string, enabled: boolean) => ({
    workspace_id: 'workspace_bkk_invoice_system',
    enabled,
    workspace_enabled: {
      workspace_bkk_invoice_system: enabled,
    },
  })),
}));

import { patchWorkspaceWorkerEnabled } from '../api/worker-scheduler-api';
import { useWorkspaceWorkerSwitches } from './useWorkspaceWorkerSwitches';

describe('useWorkspaceWorkerSwitches', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('defaults missing workspaces to on and respects overlay off', async () => {
    const api = useWorkspaceWorkerSwitches({ autoLoad: false, pollMs: 0 });
    await api.reloadWorkspaceSwitches();
    expect(api.isWorkspaceWorkerOn('workspace_dashpro')).toBe(true);
    expect(api.isWorkspaceWorkerOn('workspace_bkk_invoice_system')).toBe(false);
  });

  it('patches workspace worker enabled state', async () => {
    const api = useWorkspaceWorkerSwitches({ autoLoad: false, pollMs: 0 });
    await api.reloadWorkspaceSwitches();
    const ok = await api.setWorkspaceWorkerOn('workspace_bkk_invoice_system', true);
    expect(ok).toBe(true);
    expect(patchWorkspaceWorkerEnabled).toHaveBeenCalledWith(
      'workspace_bkk_invoice_system',
      true,
    );
    expect(api.isWorkspaceWorkerOn('workspace_bkk_invoice_system')).toBe(true);
  });
});
