import { afterEach, describe, expect, it, vi } from 'vitest';

import {
  adviseAutoAttendKey,
  maybeTriggerAutoAttendAdvise,
  resetAutoAttendAdviseMemoryForTests,
  shouldAutoAttendAdvise,
} from './vaxon-auto-attend-advise';

vi.mock('../api/autonomy-api', () => ({
  triggerAutonomyScan: vi.fn().mockResolvedValue({ created_count: 1 }),
}));

import { triggerAutonomyScan } from '../api/autonomy-api';

describe('vaxon-auto-attend-advise', () => {
  afterEach(() => {
    resetAutoAttendAdviseMemoryForTests();
    vi.clearAllMocks();
  });

  it('keys auto-attend switch actions', () => {
    expect(
      adviseAutoAttendKey({
        type: 'switch_workspace',
        workspace_id: 'workspace_dashpro',
        signal_id: 'sig-1',
        auto_attend: true,
      }),
    ).toBe('workspace_dashpro:sig-1');
    expect(
      adviseAutoAttendKey({
        type: 'switch_workspace',
        workspace_id: 'workspace_dashpro',
        auto_attend: false,
      }),
    ).toBeNull();
  });

  it('only auto-attends under Full autonomy', () => {
    const action = {
      type: 'switch_workspace' as const,
      workspace_id: 'workspace_dashpro',
      auto_attend: true,
    };
    expect(shouldAutoAttendAdvise({ autonomyMode: 'full', adviseUiAction: action })).toBe(true);
    expect(shouldAutoAttendAdvise({ autonomyMode: 'semi', adviseUiAction: action })).toBe(false);
  });

  it('triggers one attend scan per advise key', async () => {
    const action = {
      type: 'switch_workspace' as const,
      workspace_id: 'workspace_dashpro',
      signal_id: 'sig-dash',
      auto_attend: true,
    };
    await expect(
      maybeTriggerAutoAttendAdvise({ autonomyMode: 'full', adviseUiAction: action }),
    ).resolves.toBe(true);
    await expect(
      maybeTriggerAutoAttendAdvise({ autonomyMode: 'full', adviseUiAction: action }),
    ).resolves.toBe(false);
    expect(triggerAutonomyScan).toHaveBeenCalledTimes(1);
  });

  it('does not scan in manual mode or for an operator-gated advise', async () => {
    await expect(
      maybeTriggerAutoAttendAdvise({
        autonomyMode: 'manual',
        adviseUiAction: {
          type: 'switch_workspace',
          workspace_id: 'workspace_dashpro',
          auto_attend: true,
        },
      }),
    ).resolves.toBe(false);
    await expect(
      maybeTriggerAutoAttendAdvise({
        autonomyMode: 'full',
        adviseUiAction: {
          type: 'switch_workspace',
          workspace_id: 'workspace_dashpro',
          auto_attend: false,
        },
      }),
    ).resolves.toBe(false);
    expect(triggerAutonomyScan).not.toHaveBeenCalled();
  });
});
