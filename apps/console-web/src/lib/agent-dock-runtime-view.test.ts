import { describe, expect, it } from 'vitest';

import { buildAgentDockRuntimeChip } from './agent-dock-runtime-view';

describe('buildAgentDockRuntimeChip', () => {
  it('returns loading copy while runtime status is unresolved', () => {
    expect(
      buildAgentDockRuntimeChip({
        runtimeStatus: null,
        loadState: 'loading',
      }).tone,
    ).toBe('loading');
  });

  it('summarizes the default runtime target when loaded', () => {
    const chip = buildAgentDockRuntimeChip({
      loadState: 'loaded',
      runtimeStatus: {
        updated_at: '2026-07-06T06:00:00Z',
        default_runtime: 'cursor_local',
        local: [
          {
            id: 'cursor_local',
            family: 'Cursor',
            label: 'Cursor local',
            target_type: 'local',
            available: true,
            binary: 'cursor',
            ready: true,
            mode_support: ['agent'],
            auth: { logged_in: true, message: 'CLI ready' },
          },
        ],
        cloud: [],
      },
    });

    expect(chip.label).toBe('Cursor local');
    expect(chip.tone).toBe('ready');
    expect(chip.detail).toContain('CLI ready');
  });

  it('surfaces vault locked posture when runtime vault is locked', () => {
    const chip = buildAgentDockRuntimeChip({
      loadState: 'loaded',
      runtimeStatus: {
        updated_at: '2026-07-06T06:00:00Z',
        default_runtime: 'cursor_local',
        vault_runtime: {
          unlocked: false,
          posture: 'vault_locked',
          hint: 'Unlock /vault to inject provider keys into CLI runtimes.',
        },
        local: [
          {
            id: 'cursor_local',
            family: 'cursor',
            label: 'Cursor local',
            target_type: 'local',
            available: true,
            binary: 'cursor',
            ready: false,
            mode_support: ['agent'],
            auth: {
              logged_in: false,
              vault_posture: 'vault_locked',
              message: 'Unlock /vault',
            },
          },
        ],
        cloud: [],
      },
    });

    expect(chip.tone).toBe('vault');
    expect(chip.vaultAction).toBe(true);
    expect(chip.detail).toContain('/vault');
  });
});
