import { describe, expect, it, vi } from 'vitest';

import { executeReportTheaterAction } from './report-theater-execute';

describe('executeReportTheaterAction', () => {
  it('switches workspace before focusing the promised signal', async () => {
    const calls: string[] = [];
    const shell = {
      setCurrentWorkspace: vi.fn((workspaceId: string) => calls.push(`workspace:${workspaceId}`)),
      focusMissionControl: vi.fn(() => calls.push('mission-control')),
      focusAttentionSidebar: vi.fn((signalId?: string | null) => calls.push(`signal:${signalId}`)),
      setLeftSidebarMode: vi.fn(() => calls.push('attention')),
      handoffSignalToIde: vi.fn(
        async (
          signal: { workspace_id?: string | null },
          options?: { autoSubmit?: boolean },
        ) => {
          calls.push(`start:${signal.workspace_id}:${String(options?.autoSubmit)}`);
        },
      ),
      focusCommandSeam: vi.fn(),
    };

    const result = await executeReportTheaterAction(shell, null, {
      action_id: 'review-axon',
      kind: 'review_signal',
      title: 'Axon-X GitHub warning',
      detail: 'Review',
      workspace_id: 'workspace_axon_watch',
      run_id: null,
      signal_id: 'signal_axon',
    });

    expect(result.ok).toBe(true);
    expect(calls).toEqual([
      'workspace:workspace_axon_watch',
      'mission-control',
      'signal:signal_axon',
      'attention',
      'start:workspace_axon_watch:true',
    ]);
  });

  it('opens Vault for theater runtime recovery actions', async () => {
    const openVaultSurface = vi.fn();
    const shell = {
      focusMissionControl: vi.fn(),
      focusAttentionSidebar: vi.fn(),
      handoffSignalToIde: vi.fn(),
      focusCommandSeam: vi.fn(),
      openVaultSurface,
    };

    const result = await executeReportTheaterAction(shell, null, {
      action_id: 'theater_open_vault',
      kind: 'inspect_runtime',
      title: 'Open Vault',
      detail: 'Unlock Vault so CLI and neural voice can recover.',
      workspace_id: null,
      run_id: null,
      signal_id: null,
    });

    expect(result).toEqual({ ok: true, kind: 'inspect_runtime' });
    expect(openVaultSurface).toHaveBeenCalledTimes(1);
    expect(shell.focusCommandSeam).not.toHaveBeenCalled();
  });
});
