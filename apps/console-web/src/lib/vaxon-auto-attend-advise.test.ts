import { beforeEach, describe, expect, it, vi } from 'vitest';

import { triggerAutonomyScan } from '../api/autonomy-api';
import {
  maybeTriggerAutoAttendAdvise,
  resetAutoAttendAdviseDedupeForTests,
} from './vaxon-auto-attend-advise';

vi.mock('../api/autonomy-api', () => ({
  triggerAutonomyScan: vi.fn().mockResolvedValue({}),
}));

describe('maybeTriggerAutoAttendAdvise', () => {
  beforeEach(() => {
    vi.mocked(triggerAutonomyScan).mockClear();
    resetAutoAttendAdviseDedupeForTests();
  });

  it('starts one background scan for a Full-autonomy attend advise', () => {
    const input = {
      autonomyMode: 'full',
      adviseUiAction: {
        type: 'switch_workspace',
        workspace_id: 'workspace_dashpro',
        signal_id: 'signal_critical',
        auto_attend: true,
      },
    };

    expect(maybeTriggerAutoAttendAdvise(input)).toBe(true);
    expect(maybeTriggerAutoAttendAdvise(input)).toBe(false);
    expect(triggerAutonomyScan).toHaveBeenCalledTimes(1);
  });

  it('does not scan in manual mode or for an operator-gated advise', () => {
    expect(
      maybeTriggerAutoAttendAdvise({
        autonomyMode: 'manual',
        adviseUiAction: {
          type: 'switch_workspace',
          workspace_id: 'workspace_dashpro',
          auto_attend: true,
        },
      }),
    ).toBe(false);
    expect(
      maybeTriggerAutoAttendAdvise({
        autonomyMode: 'full',
        adviseUiAction: {
          type: 'switch_workspace',
          workspace_id: 'workspace_dashpro',
          auto_attend: false,
        },
      }),
    ).toBe(false);
    expect(triggerAutonomyScan).not.toHaveBeenCalled();
  });
});
